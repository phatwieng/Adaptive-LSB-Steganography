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
REDUNDANCY = 3 

def encode_LSB(image_path, plaintext, password, output_path):
    """Encodes with Manual Bit-Packing for absolute cross-platform integrity."""
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
            streamer = BmpStreamer(temp_bmp); streamer.create_empty(width, height)
            
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
            
            # 1. Prepare Header Bits (Manual Big-Endian)
            h_bits = []
            for i in range(31, -1, -1):
                h_bits.append((payload_bit_length >> i) & 1)
            
            # 2. Fixed Header Placement (Majority Vote logic)
            h_indices = []
            for i, bit in enumerate(h_bits):
                for r in range(REDUNDANCY):
                    idx = i * REDUNDANCY + r
                    img_array[0, idx, 0] = (img_array[0, idx, 0] & 0xFE) | bit
                    h_indices.append((0 * cols * ch) + (idx * ch) + 0)
            
            # 3. Adaptive Data
            AdaptiveLSBCore(password=password).encode(img_array, protected_bytes, forbidden_indices=set(h_indices))
            img_array.flush()

        # ── FINALIZATION ──
        if output_ext == '.bmp':
            if os.path.exists(output_path): os.remove(output_path)
            shutil.move(temp_bmp, output_path)
        else:
            with Image.open(temp_bmp) as final_bmp:
                final_bmp.save(output_path, "PNG", compress_level=0)

        log_event("ENCODE", "SUCCESS", f"Stored in {output_path}")
        return f"Successfully encoded in {output_path}"

    except Exception as e:
        log_event("ENCODE", "ERROR", str(e)); raise e
    finally:
        if temp_bmp and os.path.exists(temp_bmp): os.remove(temp_bmp)
