import numpy as np
import cv2
from scipy import stats
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

def fast_entropy(arr):
    img = (arr * 255).astype(np.uint8) if arr.dtype != np.uint8 else arr
    h = np.bincount(img.ravel(), minlength=256)
    h = h / (h.sum() + 1e-10)
    return -np.sum(h[h > 0] * np.log2(h[h > 0]))

def analyze_lsb_pairing(img_uint):
    """Chi-Square Attack: High risk if LSB pairs are randomized (high p-value)."""
    try:
        def get_risk(ch):
            hist = np.bincount(ch.ravel(), minlength=256)
            y_e, y_o = hist[0::2].astype(np.float64), hist[1::2].astype(np.float64)
            exp = (y_e + y_o) / 2.0
            mask = exp > 10
            if np.sum(mask) < 5: return 0.0
            
            chi = np.sum(((y_e[mask] - exp[mask])**2) / (exp[mask] + 1e-10))
            df = np.sum(mask) - 1
            ratio = chi / (df + 1e-10)
            
            # ── RATIO SCORING ──
            if ratio <= 1.0: return 1.0
            if ratio > 10.0: return 0.0
            return 1.0 - ((ratio - 1.0) / 9.0)

        if len(img_uint.shape) == 3:
            return max([get_risk(img_uint[:,:,i]) for i in range(3)])
        return get_risk(img_uint)
    except: return 0.0

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
