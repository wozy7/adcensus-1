import os
import pickle
import sys

from scipy.ndimage.filters import median_filter
import numpy as np
from PIL import Image

import pyximport; pyximport.install()
import main_

DEBUG = 1
IMG_DIR = ''

def match(x0, x1):
    # ad
    ad_vol = main_.ad_vol(x0, x1)

    if DEBUG:
        pred = ad_vol.argmin(0).astype(np.float64) * scale
        Image.fromarray(pred.astype(np.uint8)).save(os.path.join(IMG_DIR, 'absdiff_vol.png'))

    # census
    x0c = main_.census_transform(x0)
    x1c = main_.census_transform(x1)
    census_vol = np.ones((disp_max, height, width)) * np.inf
    for i in range(disp_max):
        census_vol[i,:,i:] = np.sum(x0c[:,i:] != x1c[:,:width - i], 2)
    census_vol /= 3

    if DEBUG:
        pred = census_vol.argmin(0).astype(np.float64) * scale
        Image.fromarray(pred.astype(np.uint8)).save(os.path.join(IMG_DIR, 'census_vol.png'))

    # adcensus
    def rho(c, lambda_):
        return 1 - np.exp(-c / lambda_)

    ad_vol_robust = rho(ad_vol, 10)
    census_vol_robust = rho(census_vol, 30)
    adcensus_vol = ad_vol_robust + census_vol_robust

    if DEBUG:
        pred = adcensus_vol.argmin(0).astype(np.float64) * scale
        Image.fromarray(pred.astype(np.uint8)).save(os.path.join(IMG_DIR, 'adcensus_vol.png'))

    # cbca
    x0c = main_.cross(x0)
    x1c = main_.cross(x1)

    for i in range(2):
        adcensus_vol = main_.cbca(x0c, x1c, adcensus_vol, 0)
        adcensus_vol = main_.cbca(x0c, x1c, adcensus_vol, 1)
        
    if DEBUG:
        pred = adcensus_vol.argmin(0).astype(np.float64) * scale
        Image.fromarray(pred.astype(np.uint8)).save(os.path.join(IMG_DIR, 'cbca_vol.png'))

    # semi-global matching
    c2_vol = main_.sgm(x0, x1, adcensus_vol)

    if DEBUG:
        pred = c2_vol.argmin(0).astype(np.float64) * scale
        Image.fromarray(pred.astype(np.uint8)).save(os.path.join(IMG_DIR, 'sgm_vol.png'))

    return c2_vol

#stereo_pairs = [['cones', 60, 4]]
#stereo_pairs = [['tsukuba', 16, 16]]
stereo_pairs = [['teddy', 60, 4]]
stereo_pairs = [['tsukuba', 16, 16], ['venus', 20, 8], ['teddy', 60, 4], ['cones', 60, 4]]
for pair_name, disp_max, scale in stereo_pairs:
    print(pair_name)
    x0 = np.array(Image.open('data/stereo-pairs/%s/imL.png' % pair_name), dtype=np.float64)
    x1 = np.array(Image.open('data/stereo-pairs/%s/imR.png' % pair_name), dtype=np.float64)
    height = x0.shape[0]
    width = x0.shape[1]
    main_.init(height, width, disp_max)
    x0c = main_.cross(x0)
    x1c = main_.cross(x1)

    c2_1 = match(x1[:,::-1], x0[:,::-1])[:,:,::-1]
    c2_0 = match(x0, x1)

    d0 = np.argmin(c2_0, 0)
    d1 = np.argmin(c2_1, 0)

    outlier = main_.outlier_detection(d0, d1)

    if DEBUG:
        img = x0.copy()
        img[outlier != 0] = 0
        img[outlier == 1, 0] = 255
        img[outlier == 2, 1] = 255
        Image.fromarray(img.astype(np.uint8)).save(os.path.join(IMG_DIR, 'outlier.png'))

    for i in range(6):
        d0, outlier = main_.iterative_region_voting(x0c, d0, outlier)

    if DEBUG: 
        Image.fromarray((d0 * scale).astype(np.uint8)).save(os.path.join(IMG_DIR, 
            'iterative_region_voting.png'))
        img = x0.copy()
        img[outlier != 0] = 0
        img[outlier == 1, 0] = 255
        img[outlier == 2, 1] = 255
        Image.fromarray(img.astype(np.uint8)).save(os.path.join(IMG_DIR, 'outlier2.png'))

    d0 = main_.proper_interpolation(x0, d0, outlier)
    if DEBUG: Image.fromarray((d0 * scale).astype(np.uint8)).save(os.path.join(IMG_DIR, 
        'proper_interpolation.png'))
    d0 = main_.depth_discontinuity_adjustment(d0, c2_0)
    if DEBUG: Image.fromarray((d0 * scale).astype(np.uint8)).save(os.path.join(IMG_DIR, 
        'depth_discontinuity_adjustment.png'))
    d0 = main_.subpixel_enhancement(d0, c2_0)
    if DEBUG: Image.fromarray((d0 * scale).astype(np.uint8)).save(os.path.join(IMG_DIR, 
        'subpixel_enhancement.png'))
    d0 = median_filter(d0, size=3, mode='constant')

    pred = d0.astype(np.float64) * scale
    Image.fromarray(pred.astype(np.uint8)).save('res.py/%s.png' % pair_name)
