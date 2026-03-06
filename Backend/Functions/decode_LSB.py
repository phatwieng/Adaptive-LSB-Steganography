import numpy as np
import os, tempfile, gc, cv2
from PIL import Image
from .AES_256 import SecureAESCipher
from .decide import AdaptiveLSBCore
from .logger import log_event
from .ecc import HammingCode
from .utils import get_seed_from_password
from .bmp_stream import BmpStreamer

HEADER_BITS = 32
REDUNDANCY = 3

def decode_LSB(image_path, password):
    """
    Decodes secret message from stego image.
    Uses BmpStreamer (mmap) for BMP files to support Gigapixel scaling.
    Uses OpenCV for standard PNG files.
    """
    try:
        ext = os.path.splitext(image_path)[1].lower()
        
        if ext == '.bmp':
            # ── GIGAPIXEL DECODING (mmap) ──
            log_event("DECODE", "INFO", f"Opening BMP via mmap: {image_path}")
            streamer = BmpStreamer(image_path)
            # Use context manager to ensure mmap is released immediately
            with streamer.open(mode='r') as img_rgb:
                return _process_decoding(img_rgb, password)
        else:
            # ── STANDARD DECODING (OpenCV) ──
            log_event("DECODE", "INFO", f"Opening image via OpenCV: {image_path}")
            img_bgr = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if img_bgr is None: return "Error: Could not load image"
            
            # Convert to RGB for consistency
            if len(img_bgr.shape) == 3:
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            else:
                img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2RGB)
            
            res = _process_decoding(img_rgb, password)
            del img_rgb, img_bgr
            return res

    except Exception as e:
        log_event("DECODE", "ERROR", str(e))
        return f"Error: {str(e)}"
    finally:
        gc.collect()

def _process_decoding(img_rgb, password):
    """Internal shared logic for bit extraction and decryption."""
    rows, cols, ch = img_rgb.shape
    
    # 1. Extract Header (Fixed placement at Row 0, Red Channel)
    voted_bits = []
    h_indices = []
    for i in range(HEADER_BITS):
        bit_copies = []
        for r in range(REDUNDANCY):
            idx = i * REDUNDANCY + r
            val = int(img_rgb[0, idx, 0] & 1)
            bit_copies.append(val)
            h_indices.append((0 * cols * ch) + (idx * ch) + 0)
        voted_bits.append(1 if sum(bit_copies) > (REDUNDANCY // 2) else 0)
    
    # 2. Reconstruct Payload Length (Big-Endian)
    payload_bit_length = 0
    for b in voted_bits:
        payload_bit_length = (payload_bit_length << 1) | b
    
    log_event("DECODE", "INFO", f"Extracted bit_length header: {payload_bit_length}")
    
    if payload_bit_length <= 0 or payload_bit_length > img_rgb.size:
        return "Error: Invalid header or corrupted file."

    # 3. Extract Adaptive Data
    core = AdaptiveLSBCore(password=password)
    protected_bytes = core.decode(img_rgb, payload_bit_length, forbidden_indices=set(h_indices))
    
    # 4. Truncate to exact length
    raw_bits = np.unpackbits(np.frombuffer(protected_bytes, dtype=np.uint8))[:payload_bit_length]
    protected_bytes_exact = np.packbits(raw_bits).tobytes()

    # 5. Robustness Layer (Hamming SEC-DED)
    encrypted_bytes = HammingCode().decode(protected_bytes_exact)
    
    # 6. Cryptography Layer (AES-256 GCM)
    plaintext = SecureAESCipher(password).decrypt(encrypted_bytes)
    
    log_event("DECODE", "SUCCESS", f"Recovered {len(plaintext)} characters")
    return plaintext
