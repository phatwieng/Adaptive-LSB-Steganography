import numpy as np  
import cv2, io, base64, os
from PIL import Image
from typing import Dict, Any, Optional  
import logging  

# ── METRIC MODULES ──
from .metrics import calculate_psnr, calculate_mse, calculate_ssim
from .spatial import analyze_pixel_differences, analyze_spatial_distribution
from .statistical import analyze_lsb_pairing, analyze_histogram_changes, analyze_correlation, analyze_noise_characteristics, fast_entropy
from .frequency import analyze_frequency_signature

logger = logging.getLogger(__name__)  
FAST_DIM, SSIM_DIM = 2048, 1024  
BLOCK_SIZE, NUM_SAMPLES = 512, 128

def get_stochastic_samples(path1, path2):
    """Randomly samples full-resolution blocks for accurate metrics."""
    try:
        with Image.open(path1) as img1, Image.open(path2) as img2:
            w, h = img1.size
            w, h = min(w, img2.size[0]), min(h, img2.size[1])
            samples1, samples2 = [], []
            rng = np.random.default_rng(int(os.path.getsize(path1)) % 1000000)
            
            if w <= FAST_DIM and h <= FAST_DIM:
                return [np.array(img1.convert("RGB"))], [np.array(img2.convert("RGB"))]

            for _ in range(NUM_SAMPLES):
                x, y = rng.integers(0, w - BLOCK_SIZE), rng.integers(0, h - BLOCK_SIZE)
                box = (x, y, x + BLOCK_SIZE, y + BLOCK_SIZE)
                samples1.append(np.array(img1.crop(box).convert("RGB")))
                samples2.append(np.array(img2.crop(box).convert("RGB")))
            return samples1, samples2
    except Exception as e:
        logger.error(f"Sampling error: {e}"); return [], []

def get_histogram_arrays(arr):
    img = (arr * 255).astype(np.uint8) if arr.dtype != np.uint8 else arr
    return {c: np.bincount(img[:, :, i].ravel(), minlength=256).tolist() for i, c in enumerate(['red', 'green', 'blue'])}

def get_bit_plane_analysis(stego_uint):
    try:
        small = cv2.resize(stego_uint, (64, 64), interpolation=cv2.INTER_AREA)
        res = {}
        for i, ch in enumerate(['red', 'green', 'blue']):
            res[ch] = {}
            for bit in range(8):
                plane = (small[:, :, i] >> bit) & 1
                _, buf = cv2.imencode('.png', (plane * 255).astype(np.uint8))
                res[ch][f'bit{bit}'] = {
                    'image': base64.b64encode(buf).decode('utf-8'),
                    'entropy': float(fast_entropy(plane)),
                    'percent_changed': float(np.mean(plane) * 100)
                }
        return res
    except: return {}

def load_image_safe(path, max_dim=None):  
    try:  
        with Image.open(path) as img:
            if max_dim: img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
            return np.array(img.convert("RGB"))
    except: return None  

def calculate_quality_score(r):  
    try:  
        w = {'psnr': 0.15, 'ssim': 0.15, 'lsb': 0.25, 'freq': 0.20, 'hist': 0.15, 'corr': 0.10}  
        psnr, ssim = r.get('psnr', 0), r.get('ssim', 0)
        risk = r.get('stealth_metrics', {}).get('chi_square_risk', 0)
        freq = r.get('stealth_metrics', {}).get('frequency_fidelity', 0)
        hist = r.get('histogram_statistics', {}).get('kl_divergence', 0)
        corr = r.get('correlation_analysis', {}).get('overall_correlation', 0)
        score = (w['psnr'] * min(psnr/50, 1) + w['ssim'] * ssim + w['lsb'] * (1-risk) + 
                 w['freq'] * max(0, freq) + w['hist'] * (1 - min(hist/2, 1)) + w['corr'] * max(0, corr))
        return float(score * 100)  
    except: return 0.0  

def comprehensive_analysis(path1, path2):
    try:
        orig_low = load_image_safe(path1, FAST_DIM)
        stego_low = load_image_safe(path2, FAST_DIM)
        if orig_low is None or stego_low is None: return {"error": "Load failed"}
        o_f, s_f = orig_low.astype(np.float32)/255.0, stego_low.astype(np.float32)/255.0
        
        s1, s2 = get_stochastic_samples(path1, path2)
        all_p, all_m, all_s, all_r = [], [], [], []
        for a, b in zip(s1, s2):
            all_p.append(calculate_psnr(a, b))
            all_m.append(calculate_mse(a, b))
            all_r.append(analyze_lsb_pairing(b))
            if len(all_s) < 8: all_s.append(calculate_ssim(a.astype(np.float32)/255.0, b.astype(np.float32)/255.0))

        pv, mv, sv, rv = float(np.mean(all_p)), float(np.mean(all_m)), float(np.mean(all_s)), float(np.mean(all_r))
        rs_score = rs_analysis(stego_low)
        spa_score = sample_pair_analysis(stego_low)
        
        freq = analyze_frequency_signature(orig_low, stego_low)
        hist = analyze_histogram_changes(o_f, s_f)
        corr = analyze_correlation(o_f, s_f)
        pd = analyze_pixel_differences(o_f, s_f)
        
        return {
            'psnr': pv, 'mse': mv, 'ssim': sv,
            'stealth_metrics': {
                'chi_square_risk': rv, 
                'rs_estimate': rs_score,
                'spa_estimate': spa_score,
                'frequency_fidelity': freq['frequency_fidelity'],
                'stealth_score': calculate_quality_score({
                    'psnr': pv, 'ssim': sv, 'stealth_metrics': {'chi_square_risk': rv, 'frequency_fidelity': freq['frequency_fidelity']},
                    'histogram_statistics': hist, 'correlation_analysis': corr
                })
            },
            'pixel_differences': {'overall': {'percent_changed': pd['changed_pixels_ratio']*100, 'mean_difference': pd['mean_diff'], 'max_difference': pd['max_diff'], 'std_difference': pd['std_diff']}},
            'spatial_distribution': analyze_spatial_distribution(o_f, s_f),
            'histogram_original': get_histogram_arrays(orig_low), 'histogram_stego': get_histogram_arrays(stego_low),
            'histogram_statistics': hist, 'correlation_analysis': corr,
            'noise_analysis': analyze_noise_characteristics(o_f, s_f), 'bit_plane_analysis': get_bit_plane_analysis(stego_low)
        }
    except Exception as e:
        logger.exception("Analysis error"); return {"error": str(e)}

def generate_analysis_report(res):  
    if "error" in res: return f"Error: {res['error']}"  
    sm = res.get('stealth_metrics', {})
    return f"--- STEALTH ANALYSIS ---\nScore: {sm.get('stealth_score',0):.2f}\nRisk: {sm.get('chi_square_risk',0)*100:.2f}%\nPSNR: {res.get('psnr',0):.2f}dB\nSSIM: {res.get('ssim',0):.4f}"
