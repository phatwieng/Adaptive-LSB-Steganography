import numpy as np
from PIL import Image
from scipy.signal import convolve2d

def calculate_psnr(original_path, stego_path):
    """Peak Signal-to-Noise Ratio: Higher is better (>40dB is excellent)."""
    img1 = np.array(Image.open(original_path).convert("RGB"), dtype=np.float64)
    img2 = np.array(Image.open(stego_path).convert("RGB"), dtype=np.float64)
    
    mse = np.mean((img1 - img2) ** 2)
    if mse == 0:
        return 100.0
    
    pixel_max = 255.0
    return 20 * np.log10(pixel_max / np.sqrt(mse))

def detect_lsb_signature(image_path):
    """
    Simple Chi-Square Analysis (Simplified):
    Detects if LSB pairs are becoming suspiciously equal.
    Returns a 'Detection Risk' score from 0.0 to 1.0.
    """
    img = np.array(Image.open(image_path).convert("L")) # Grayscale for speed
    hist, _ = np.histogram(img, bins=256, range=(0, 256))
    
    # Check pairs (0,1), (2,3), etc.
    even_indices = np.arange(0, 256, 2)
    odd_indices = np.arange(1, 256, 2)
    
    observed_even = hist[even_indices]
    observed_odd = hist[odd_indices]
    
    expected = (observed_even + observed_odd) / 2.0
    
    # Avoid division by zero
    mask = expected > 0
    chi_sq = np.sum(((observed_even[mask] - expected[mask])**2) / expected[mask])
    
    # Normalized risk (heuristic)
    risk = min(1.0, chi_sq / 1000.0) 
    return 1.0 - risk # Higher is better/safer

def get_stealth_report(original_path, stego_path):
    psnr = calculate_psnr(original_path, stego_path)
    risk = detect_lsb_signature(stego_path)
    
    quality = "EXCELLENT" if psnr > 45 else "GOOD" if psnr > 35 else "POOR"
    
    return {
        "psnr_db": round(psnr, 2),
        "stealth_score": round(risk * 100, 1),
        "quality_assessment": quality,
        "advice": "Safe to use." if quality != "POOR" else "Warning: Visible distortion. Use a larger image."
    }
