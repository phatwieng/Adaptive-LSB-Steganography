import numpy as np
import cv2
import logging
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)

def calculate_psnr(a1, a2):
    """Calculates PSNR with high precision (64-bit)."""
    try:
        err = np.mean((a1.astype(np.float64) - a2.astype(np.float64))**2)
        if err == 0: return 100.0
        return float(20 * np.log10(255.0 / np.sqrt(err)))
    except: return 0.0

def calculate_mse(a1, a2):
    return float(np.mean((a1.astype(np.float64) - a2.astype(np.float64))**2))

def calculate_ssim(a1, a2):
    try:
        return float(ssim(a1, a2, channel_axis=2, data_range=1.0) if len(a1.shape)==3 else ssim(a1, a2, data_range=1.0))
    except: return 0.0
