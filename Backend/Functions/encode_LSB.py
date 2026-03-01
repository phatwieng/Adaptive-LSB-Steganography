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

def encode_LSB(image_path, plaintext, password, output_path):
    """Full-cycle encoding with Fixed Header placement for absolute integrity."""
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
            # 1. Fixed Header (First 32 pixels of channel 0 - Red)
            h_bits = np.unpackbits(np.array([payload_bit_length], dtype=">u4").view(np.uint8))
            for i in range(HEADER_BITS):
                # Using first 32 pixels of row 0
                img_array[0, i, 0] = (img_array[0, i, 0] & 0xFE) | h_bits[i]
            
            # 2. Adaptive Data (Skipping the header zone)
            AdaptiveLSBCore(password=password).encode(img_array, protected_bytes, forbidden_indices=set(range(HEADER_BITS)))
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
