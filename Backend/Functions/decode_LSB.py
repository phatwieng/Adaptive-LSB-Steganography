import numpy as np
import os, tempfile, gc
from PIL import Image
from .AES_256 import SecureAESCipher
from .decide import AdaptiveLSBCore
from .logger import log_event
from .ecc import HammingCode
from .utils import get_seed_from_password

HEADER_BITS = 32

def decode_LSB(image_path, password):
    """Full-cycle decoding with Fixed Header extraction."""
    temp_path = None
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            shape = (height, width, 3)
            fd, temp_path = tempfile.mkstemp(suffix='.dat')
            os.close(fd)
            temp_memmap = np.memmap(temp_path, dtype=np.uint8, mode='w+', shape=shape)
            
            chunk_rows = max(1, 100 * 1024 * 1024 // (width * 3))
            for y in range(0, height, chunk_rows):
                end_y = min(y + chunk_rows, height)
                temp_memmap[y:end_y] = np.array(img.crop((0, y, width, end_y)).convert("RGB"), dtype=np.uint8)
            temp_memmap.flush()

        img_array = np.memmap(temp_path, dtype=np.uint8, mode='r', shape=shape)

        # ── FIXED HEADER EXTRACTION ──
        # Header is in the first 32 pixels of row 0, Red channel (channel 0)
        h_bits = []
        for i in range(HEADER_BITS):
            h_bits.append(img_array[0, i, 0] & 1)
        
        payload_bit_length = int(np.packbits(np.array(h_bits, dtype=np.uint8)).view(">u4")[0])
        log_event("DECODE", "INFO", f"Extracted payload_bit_length: {payload_bit_length}")
        
        if payload_bit_length <= 0 or payload_bit_length > img_array.size:
            return "Error: Invalid payload length or corrupted data."

        # ── DATA EXTRACTION ──
        # Skip the first 32 bits (header zone)
        protected_bytes = AdaptiveLSBCore(password=password).decode(img_array, payload_bit_length, forbidden_indices=set(range(HEADER_BITS)))
        
        # Exact truncation
        bits = np.unpackbits(np.frombuffer(protected_bytes, dtype=np.uint8))[:payload_bit_length]
        protected_bytes_exact = np.packbits(bits).tobytes()

        # AES Decryption
        encrypted_bytes = HammingCode().decode(protected_bytes_exact)
        plaintext = SecureAESCipher(password).decrypt(encrypted_bytes)
        
        log_event("DECODE", "SUCCESS", f"Extracted {len(plaintext)} bytes")
        return plaintext

    except Exception as e:
        log_event("DECODE", "ERROR", str(e))
        return f"Error: {str(e)}"
    finally:
        if 'img_array' in locals(): del img_array
        gc.collect()
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)
