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
        """Creates a raw 24-bit BMP file skeleton."""
        stride = ((w * 3 + 3) // 4) * 4
        size = 54 + (stride * abs(h))
        with open(self.filepath, 'wb') as f:
            # 18 args: 1,2:cc(B,M), 3:I(size), 4,5:HH(res), 6:I(off), 7:I(hdr), 8,9:ii(w,h), 10:H(planes), 11:H(bit), 12:I(comp), 13:I(img_sz), 14,15:ii(res), 16,17:II(clr), 18:PaddingArg
            # Fixing logic: The format string below has 18 slots. We must provide 18 arguments.
            f.write(struct.pack('<ccIHHiIIiiHHIIiiII', b'B', b'M', size, 0, 0, 54, 40, w, h, 1, 24, 0, size-54, 2835, 2835, 0, 0, 0))
            f.seek(size - 1); f.write(b'\0')

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
