from .encode_LSB import encode_LSB
from .decode_LSB import decode_LSB
from .decide import AdaptiveLSBCore
from .bmp_stream import BmpStreamer
from PIL import Image
import numpy as np
import os, tempfile

def encode_message(img_path, msg, pwd, out_path):
    return encode_LSB(img_path, msg, pwd, out_path)

def decode_message(img_path, pwd):
    return decode_LSB(img_path, pwd)

def get_image_stats(img_path, real_capacity=False):
    """Retrieves image dimensions and embedding capacity."""
    with Image.open(img_path) as img:
        w, h = img.size
        res = {
            "width": w, "height": h, "channels": 3,
            "total_pixels": w * h,
            "theoretical_max_bits": w * h * 3 * 2, # Max 2 bits per channel
            "practical_max_bits": w * h * 3, # Safe estimate
            "max_capacity_chars": (w * h * 3) // 8,
            "capacity_type": "estimated"
        }
        
    if real_capacity:
        # Use exact exhaustive scan for huge images
        core = AdaptiveLSBCore()
        fd, tpath = tempfile.mkstemp(suffix='.bmp')
        os.close(fd)
        try:
            s = BmpStreamer(tpath); s.create_empty(w, h)
            with s.open(mode='r+') as arr:
                cap = core.calculate_capacity(arr)
                res.update({
                    "practical_max_bits": cap,
                    "max_capacity_chars": cap // 8,
                    "capacity_type": "real"
                })
        finally:
            if os.path.exists(tpath): os.remove(tpath)
    return res
