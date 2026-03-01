import numpy as np
import os, tempfile, gc
from PIL import Image
from .AES_256 import SecureAESCipher
from .decide import AdaptiveLSBCore
from .logger import log_event
from .ecc import HammingCode
from .utils import get_seed_from_password

HEADER_BITS = 32
REDUNDANCY = 3

def _header_positions(flat_size, seed):
    """Mirror encode LCG logic exactly."""
    pos = []
    curr = seed
    a, c, m = 1664525, 1013904223, 2**32
    search_space = min(flat_size, 2000000)
    total_slots = HEADER_BITS * REDUNDANCY
    while len(pos) < total_slots:
        curr = (a * curr + c) % m
        p = curr % search_space
        if p not in pos: pos.append(p)
    return np.array(pos, dtype=np.int64)

def decode_LSB(image_path, password):
    """Decodes using majority-vote on triple-redundant scattered header."""
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
        seed = get_seed_from_password(password)
        h_pos = _header_positions(img_array.size, seed)

        # ── ROBUST HEADER EXTRACTION (Majority Vote) ──
        rows, cols, ch = img_array.shape
        raw_bits = []
        for p in h_pos:
            r, cl, cn = (p // ch) // cols, (p // ch) % cols, p % ch
            raw_bits.append(img_array[r, cl, cn] & 1)
        
        # Reshape to (32 bits, 3 copies) and take majority vote
        raw_bits = np.array(raw_bits).reshape(HEADER_BITS, REDUNDANCY)
        voted_bits = (np.sum(raw_bits, axis=1) > (REDUNDANCY // 2)).astype(np.uint8)
        
        payload_bit_length = int(np.packbits(voted_bits).view(">u4")[0])
        log_event("DECODE", "INFO", f"Robust extraction bit_length: {payload_bit_length}")
        
        if payload_bit_length <= 0 or payload_bit_length > img_array.size:
            return "Error: Invalid payload length or corrupted data."

        # ── DATA EXTRACTION ──
        protected_bytes = AdaptiveLSBCore(password=password).decode(img_array, payload_bit_length, forbidden_indices=set(h_pos))
        
        # Truncate and Decrypt
        bits = np.unpackbits(np.frombuffer(protected_bytes, dtype=np.uint8))[:payload_bit_length]
        protected_bytes_exact = np.packbits(bits).tobytes()
        encrypted_bytes = HammingCode().decode(protected_bytes_exact)
        plaintext = SecureAESCipher(password).decrypt(encrypted_bytes)
        
        log_event("DECODE", "SUCCESS", f"Extracted {len(plaintext)} bytes")
        return plaintext

    except Exception as e:
        log_event("DECODE", "ERROR", str(e)); return f"Error: {str(e)}"
    finally:
        if 'img_array' in locals(): del img_array
        gc.collect()
        if temp_path and os.path.exists(temp_path): os.remove(temp_path)
