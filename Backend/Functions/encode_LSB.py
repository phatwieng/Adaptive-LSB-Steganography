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

def _header_positions(flat_size, seed):
    """Deterministic header positioning using a simple LCG."""
    pos, curr = set(), seed
    a, c, m = 1664525, 1013904223, 2**32
    search_space = min(flat_size, 1000000)
    
    while len(pos) < HEADER_BITS:
        curr = (a * curr + c) % m
        pos.add(curr % search_space)
            
    res = list(pos)
    res.sort()
    return np.array(res, dtype=np.int64)

def encode_LSB(image_path, plaintext, password, output_path):
    """Full-cycle encoding: AES -> ECC -> Adaptive LSB."""
    temp_bmp = None
    try:
        cipher = SecureAESCipher(password)
        protected_bytes = HammingCode().encode(cipher.encrypt(plaintext))
        payload_bit_length = len(protected_bytes) * 8

        # ── FORMAT HANDLING ──
        with Image.open(image_path) as img:
            width, height = img.size
            is_huge = (width * height) > (16384 * 16384)
            output_ext = ".bmp" if is_huge else ".png"
            output_path = os.path.splitext(output_path)[0] + output_ext

            # Create raw temporary BMP
            fd, temp_bmp = tempfile.mkstemp(suffix='.bmp')
            os.close(fd)
            streamer = BmpStreamer(temp_bmp)
            streamer.create_empty(width, height)
            
            chunk_rows = max(1, 256 * 1024 * 1024 // (width * 3))
            with streamer.open(mode='r+') as img_array:
                for y in range(0, height, chunk_rows):
                    end_y = min(y + chunk_rows, height)
                    region = img.crop((0, y, width, end_y)).convert("RGB")
                    img_array[y:end_y] = np.array(region, dtype=np.uint8)
                img_array.flush()

        # ── EMBEDDING ──
        streamer = BmpStreamer(temp_bmp)
        with streamer.open(mode='r+') as img_array:
            rows, cols, ch = img_array.shape
            h_bits = np.unpackbits(np.array([payload_bit_length], dtype=">u4").view(np.uint8))
            h_pos = _header_positions(img_array.size, get_seed_from_password(password))
            
            # Robust 3D Header Placement
            for i in range(HEADER_BITS):
                p = h_pos[i]
                r, cl, cn = (p // ch) // cols, (p // ch) % cols, p % ch
                img_array[r, cl, cn] = (img_array[r, cl, cn] & 0xFE) | h_bits[i]
            
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
                final_bmp.save(output_path, "PNG", optimize=False, compress_level=1)

        log_event("ENCODE", "SUCCESS", f"Stored in {output_path}")
        return f"Successfully encoded in {output_path}"

    except Exception as e:
        log_event("ENCODE", "ERROR", str(e))
        raise e
    finally:
        if temp_bmp and os.path.exists(temp_bmp): os.remove(temp_bmp)
