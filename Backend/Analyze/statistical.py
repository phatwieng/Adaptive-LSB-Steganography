import numpy as np
import cv2
from scipy import stats
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def rs_analysis(img_uint):
    """
    Standard RS Analysis (2x2 groups) using Mask [0,1,1,0].
    """
    try:
        def get_estimate(ch):
            h, w = ch.shape
            h_new, w_new = h - h % 2, w - w % 2
            blocks = ch[:h_new, :w_new].reshape(-1, 2, 2)
            def f(b): return np.sum(np.abs(b[:, :, :-1] - b[:, :, 1:]), axis=(1,2)) + np.sum(np.abs(b[:, :-1, :] - b[:, 1:, :]), axis=(1,2))
            
            s0 = f(blocks)
            
            # F1: Mask [0,1,1,0]
            b_f1 = blocks.copy(); b_f1[:, 0, 1] ^= 1; b_f1[:, 1, 0] ^= 1
            s1 = f(b_f1)
            
            # F-1: Mask [0,-1,-1,0]
            def flip_neg(x): return (x - 1) ^ 1 + 1
            b_fn1 = blocks.copy(); b_fn1[:, 0, 1] = flip_neg(b_fn1[:, 0, 1]); b_fn1[:, 1, 0] = flip_neg(b_fn1[:, 1, 0])
            sn1 = f(b_fn1)
            
            rm, sm = np.sum(s1 > s0), np.sum(s1 < s0)
            r_m, s_m = np.sum(sn1 > s0), np.sum(sn1 < s0)
            
            # p = (Rm - Sm) / ( (Rm - Sm) + (R_m - S_m) ) approx
            diff = (rm - sm) - (r_m - s_m)
            return abs(diff) / (len(blocks) + 1e-10)

        if len(img_uint.shape) == 3:
            return float(np.mean([get_estimate(img_uint[:,:,i]) for i in range(3)]))
        return get_estimate(img_uint)
    except: return 0.0

def sample_pair_analysis(img_uint):
    """
    Sample Pair Analysis (SPA).
    """
    try:
        def get_spa(ch):
            x = ch.ravel().astype(np.int32)
            pairs = x.reshape(-1, 2)
            # MSBs equal
            mask = (pairs[:, 0] >> 1) == (pairs[:, 1] >> 1)
            p_pairs = pairs[mask]
            if len(p_pairs) == 0: return 0.0
            # Natural image: m approx k (m/n approx 0.5)
            m = np.sum((p_pairs[:, 0] & 1) != (p_pairs[:, 1] & 1))
            ratio = m / len(p_pairs)
            return abs(ratio - 0.5) * 2 # Normalize deviation

        if len(img_uint.shape) == 3:
            return float(np.mean([get_spa(img_uint[:,:,i]) for i in range(3)]))
        return get_spa(img_uint)
    except: return 0.0

def analyze_lsb_pairing(img_uint):
    try:
        def get_risk(ch):
            hist = np.bincount(ch.ravel(), minlength=256)
            y_e, y_o = hist[0::2].astype(np.float64), hist[1::2].astype(np.float64)
            exp = (y_e + y_o) / 2.0
            mask = exp > 5
            if np.sum(mask) < 2: return 0.0
            chi = np.sum(((y_e[mask] - exp[mask])**2) / (exp[mask] + 1e-10))
            return float(np.clip(chi / (len(ch.ravel()) / 500), 0, 1))

        if len(img_uint.shape) == 3:
            return float(np.mean([get_risk(img_uint[:,:,i]) for i in range(3)]))
        return get_risk(img_uint)
    except: return 0.0

def fast_entropy(arr):
    img = (arr * 255).astype(np.uint8) if arr.dtype != np.uint8 else arr
    h = np.bincount(img.ravel(), minlength=256)
    h = h / (h.sum() + 1e-10)
    return -np.sum(h[h > 0] * np.log2(h[h > 0]))

def analyze_histogram_changes(a1, a2):
    def get_h(a):
        img = (a * 255).astype(np.uint8) if a.dtype != np.uint8 else a
        h = np.bincount(img.ravel(), minlength=256)
        return h / (h.sum() + 1e-10)
    h1, h2 = get_h(a1), get_h(a2)
    kl = np.sum(h2 * np.log2((h2 + 1e-10) / (h1 + 1e-10)))
    return {'histogram_difference': float(np.sum(np.abs(h1 - h2)) / 2.0), 'kl_divergence': float(max(0, kl)),
            'entropy_original': fast_entropy(a1), 'entropy_stego': fast_entropy(a2)}

def analyze_correlation(a1, a2):
    a, b = a1.ravel().astype(np.float32), a2.ravel().astype(np.float32)
    if np.all(a == b): return {'overall_correlation': 1.0}
    c = np.corrcoef(a, b)[0, 1]
    return {'overall_correlation': float(np.clip(c, -1.0, 1.0))}

def analyze_noise_characteristics(a1, a2):
    diff = a2 - a1
    nv, sv = np.var(diff), np.var(a1)
    snr = 100.0 if nv < 1e-12 else 10 * np.log10(sv / (nv + 1e-10))
    return {'noise_mean': float(np.mean(diff)), 'noise_std': float(np.std(diff)), 'snr': float(snr)}
