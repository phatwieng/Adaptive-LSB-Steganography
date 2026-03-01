import numpy as np
import logging

logger = logging.getLogger(__name__)

def analyze_pixel_differences(a1, a2):
    """Calculates granular pixel-level differences and Total Variation."""
    d = np.abs(a2 - a1)
    ch = d > 0
    
    # ── TOTAL VARIATION (Smoothness Change) ──
    # Measures how much the 'texture' of the noise changed
    tv_orig = np.sum(np.abs(np.diff(a1, axis=0))) + np.sum(np.abs(np.diff(a1, axis=1)))
    tv_stego = np.sum(np.abs(np.diff(a2, axis=0))) + np.sum(np.abs(np.diff(a2, axis=1)))
    
    return {
        'changed_pixels_ratio': float(np.mean(ch)),
        'mean_diff': float(np.mean(d)),
        'max_diff': float(np.max(d)),
        'std_diff': float(np.std(d)),
        'total_variation_diff': float(abs(tv_stego - tv_orig) / (tv_orig + 1e-10))
    }

def analyze_spatial_distribution(a1, a2):
    """Analyzes where changes are located (Top/Bottom/Left/Right/Center)."""
    d = np.abs(a2 - a1)
    h, w = d.shape[:2]
    res = {}
    
    zones = {
        'Global': d,
        'Top Half': d[:h//2, :], 'Bottom Half': d[h//2:, :],
        'Left Half': d[:, :w//2], 'Right Half': d[:, w//2:],
        'Center Region': d[h//4:3*h//4, w//4:3*w//4]
    }
    
    for name, data in zones.items():
        ratio = np.mean(data > 0)
        res[name] = {
            'percent_changed': float(ratio * 100),
            'uniformity': float(1.0 - np.std(data > 0) if data.size > 0 else 1.0)
        }
    return res
