import numpy as np
import os, shutil, tempfile, gc
from PIL import Image
from .AES_256 import SecureAESCipher
from .decide import AdaptiveLSBCore
from .logger import log_event
from .bmp_stream import BmpStreamer
from .ecc import HammingCode
from .utils import get_seed_from_password

HEADER_BITS = 32
REDUNDANCY = 3 # Each header bit is stored 3 times

def _header_positions(flat_size, seed):
    """Deterministic header positioning with Triple Redundancy."""
    pos = []
    curr = seed
    a, c, m = 1664525, 1013904223, 2**32
    # Use first 2M pixels for header scattering
    search_space = min(flat_size, 2000000)
    
    total_slots = HEADER_BITS * REDUNDANCY
    while len(pos) < total_slots:
        curr = (a * curr + c) % m
        p = curr % search_space
        if p not in pos: pos.append(p)
            
    return np.array(pos, dtype=np.int64)

def encode_LSB(image_path, plaintext, password, output_path):
    """Encodes with a scattered, triple-redundant header for max robustness."""
    temp_bmp = None
    try:
        cipher = SecureAESCipher(password)
        protected_bytes = HammingCode().encode(cipher.encrypt(plaintext))
        payload_bit_length = len(protected_bytes) * 8

        with Image.open(image_path) as img:
            width, height = img.size
            is_huge = (width * height) > (16384 * 16384)
            output_ext = ".bmp" if is_huge else ".png"
            output_path = os.path.splitext(output_path)[0] + output_ext

            fd, temp_bmp = tempfile.mkstemp(suffix='.bmp')
            os.close(fd)
            streamer = BmpStreamer(temp_bmp)
            streamer.create_empty(width, height)
            
            chunk_rows = max(1, 256 * 1024 * 1024 // (width * 3))
            with streamer.open(mode='r+') as img_array:
                for y in range(0, height, chunk_rows):
                    end_y = min(y + chunk_rows, height)
                    img_array[y:end_y] = np.array(img.crop((0, y, width, end_y)).convert("RGB"), dtype=np.uint8)
                img_array.flush()

        # ── EMBEDDING ──
        streamer = BmpStreamer(temp_bmp)
        with streamer.open(mode='r+') as img_array:
            rows, cols, ch = img_array.shape
            # 1. Prepare Header Bits with Redundancy
            h_bits = np.unpackbits(np.array([payload_bit_length], dtype=">u4").view(np.uint8))
            redundant_h_bits = np.repeat(h_bits, REDUNDANCY)
            
            # 2. Map to Scattered Positions
            h_pos = _header_positions(img_array.size, get_seed_from_password(password))
            for i in range(len(h_pos)):
                p = h_pos[i]
                r, cl, cn = (p // ch) // cols, (p // ch) % cols, p % ch
                img_array[r, cl, cn] = (img_array[r, cl, cn] & 0xFE) | redundant_h_bits[i]
            
            # 3. Adaptive Data (Skipping header slots)
            AdaptiveLSBCore(password=password).encode(img_array, protected_bytes, forbidden_indices=set(h_pos))
            img_array.flush()

        # ── FINALIZATION ──
        if output_ext == '.bmp':
            if os.path.exists(output_path): os.remove(output_path)
            import time
            for _ in range(5):
                try: shutil.move(temp_bmp, output_path); break
                except PermissionError: time.sleep(0.5)
            else: shutil.move(temp_bmp, output_path)
        else:
            with Image.open(temp_bmp) as final_bmp:
                # Force strictly lossless save
                final_bmp.save(output_path, "PNG", optimize=False, compress_level=0)

        log_event("ENCODE", "SUCCESS", f"Stored in {output_path}")
        return f"Successfully encoded in {output_path}"

    except Exception as e:
        log_event("ENCODE", "ERROR", str(e)); raise e
    finally:
        if temp_bmp and os.path.exists(temp_bmp): os.remove(temp_bmp)
