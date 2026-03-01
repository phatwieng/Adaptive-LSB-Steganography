import numpy as np
import os, struct
from contextlib import contextmanager

class BmpStreamer:
    def __init__(self, filepath):
        self.filepath = filepath
        self.offset = 54 # Standard header

    def _parse_header(self):
        with open(self.filepath, 'rb') as f:
            f.seek(18)
            self.width, self.height = struct.unpack('<ii', f.read(8))
            self.channels = 3
            self.row_stride = ((self.width * 3 + 3) // 4) * 4

    def create_empty(self, w, h):
        """Creates a raw 24-bit Top-to-Bottom BMP file skeleton."""
        stride = ((w * 3 + 3) // 4) * 4
        # Force Top-to-Bottom by using negative height
        h_top_down = -abs(h)
        img_size = stride * abs(h)
        file_size = 54 + img_size
        
        header = struct.pack('<2sIHHI', b'BM', file_size, 0, 0, 54)
        info = struct.pack('<IiiHHIIiiII', 40, w, h_top_down, 1, 24, 0, img_size, 2835, 2835, 0, 0)
        
        with open(self.filepath, 'wb') as f:
            f.write(header)
            f.write(info)
            f.seek(file_size - 1); f.write(b'\0')

    @contextmanager
    def open(self, mode='r+'):
        """Opens BMP via memmap. Robust Windows lock release."""
        self._parse_header()
        mm = None
        try:
            mm = np.memmap(self.filepath, dtype='uint8', mode=mode, offset=self.offset, shape=(abs(self.height), self.row_stride))
            view = mm[:, :self.width*3].reshape(abs(self.height), self.width, 3)
            yield view[:, :, ::-1] # Yield as RGB
        finally:
            if mm is not None:
                if mode == 'r+': mm.flush()
                # ── WINDOWS LOCK RELEASE ──
                if hasattr(mm, '_mmap') and mm._mmap: mm._mmap.close()
                del mm
                import gc; gc.collect()
