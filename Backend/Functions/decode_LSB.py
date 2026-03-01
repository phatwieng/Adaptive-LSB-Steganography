import numpy as np
import os, tempfile, gc, cv2
from .AES_256 import SecureAESCipher
from .decide import AdaptiveLSBCore
from .logger import log_event
from .ecc import HammingCode
from .utils import get_seed_from_password
from .bmp_stream import BmpStreamer

HEADER_BITS = 32
REDUNDANCY = 3

def decode_LSB(image_path, password):
    """Absolute extraction using OpenCV to avoid Pillow color drift."""
    temp_path = None
    try:
        # 1. Load using OpenCV (Strict LSB preservation)
        img_bgr = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img_bgr is None: return "Error: Could not load image"
        
        # Ensure RGB order for consistency with Encoder
        if len(img_bgr.shape) == 3:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        else:
            img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_GRAY2RGB)
            
        rows, cols, ch = img_rgb.shape
        flat_size = img_rgb.size

        # 2. Extract Header (Fixed placement at Row 0, Channel 0)
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
        
        # 3. Build Length (Big-Endian)
        payload_bit_length = 0
        for b in voted_bits:
            payload_bit_length = (payload_bit_length << 1) | b
        
        log_event("DECODE", "INFO", f"OpenCV extraction bit_length: {payload_bit_length}")
        
        if payload_bit_length <= 0 or payload_bit_length > flat_size:
            return "Error: Invalid payload length or corrupted data."

        # 4. Extract Adaptive Data
        core = AdaptiveLSBCore(password=password)
        protected_bytes = core.decode(img_rgb, payload_bit_length, forbidden_indices=set(h_indices))
        
        # 5. Bit-Perfect Truncation
        raw_bits = np.unpackbits(np.frombuffer(protected_bytes, dtype=np.uint8))[:payload_bit_length]
        protected_bytes_exact = np.packbits(raw_bits).tobytes()

        # 6. Hamming + AES
        encrypted_bytes = HammingCode().decode(protected_bytes_exact)
        plaintext = SecureAESCipher(password).decrypt(encrypted_bytes)
        
        log_event("DECODE", "SUCCESS", f"Extracted {len(plaintext)} bytes")
        return plaintext

    except Exception as e:
        log_event("DECODE", "ERROR", str(e)); return f"Error: {str(e)}"
    finally:
        if 'img_rgb' in locals(): del img_rgb
        gc.collect()
