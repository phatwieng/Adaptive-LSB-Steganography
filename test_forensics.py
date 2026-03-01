import os
import sys
import numpy as np
from PIL import Image

# Add Backend to path
sys.path.append(os.path.join(os.getcwd(), 'Steganography(Deployed)', 'Backend'))

from Functions.Stego import encode_message, decode_message, get_image_stats
from Analyze.image_analyzer import comprehensive_analysis

def simple_lsb_encode(img_path, message, out_path):
    img = Image.open(img_path).convert("RGB")
    arr = np.array(img)
    bits = np.unpackbits(np.frombuffer(message.encode('utf-8'), dtype=np.uint8))
    flat = arr.ravel()
    if len(bits) > len(flat): bits = bits[:len(flat)]
    flat[:len(bits)] = (flat[:len(bits)] & 0xFE) | bits
    Image.fromarray(flat.reshape(arr.shape)).save(out_path)

def run_forensic_test():
    test_dir = r'C:\Users\nongp\Downloads\test_images\512'
    img_name = '512.bmp'
    img_path = os.path.join(test_dir, img_name)
    
    if not os.path.exists(img_path): return

    message = "Secret Data " * 2000 
    
    # 1. CLEAN
    clean_res = comprehensive_analysis(img_path, img_path)
    # 2. SIMPLE
    simple_path = "test_simple.png"
    simple_lsb_encode(img_path, message, simple_path)
    simple_res = comprehensive_analysis(img_path, simple_path)
    # 3. ADAPTIVE
    adaptive_path = "test_adaptive.png"
    encode_message(img_path, message, "pass", adaptive_path)
    adaptive_res = comprehensive_analysis(img_path, adaptive_path)

    print("\n" + "="*60)
    print(f"{'Metric':<20} | {'Clean':<10} | {'Simple':<10} | {'Adaptive':<10}")
    print("-"*60)
    
    for label, key in [('RS Est', 'rs_estimate'), ('SPA Est', 'spa_estimate'), ('Chi-Sq', 'chi_square_risk')]:
        c = clean_res['stealth_metrics'][key] * 100
        s = simple_res['stealth_metrics'][key] * 100
        a = adaptive_res['stealth_metrics'][key] * 100
        print(f"{label:<20} | {c:>9.2f}% | {s:>9.2f}% | {a:>9.2f}%")
        
    print(f"{'PSNR':<20} | {'N/A':>10} | {simple_res['psnr']:>10.2f} | {adaptive_res['psnr']:>10.2f}")
    print("="*60)
    
    for p in [simple_path, adaptive_path]:
        if os.path.exists(p): os.remove(p)

if __name__ == "__main__":
    run_forensic_test()
