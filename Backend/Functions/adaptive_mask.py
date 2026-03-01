import numpy as np
import cv2
import hashlib

class AdaptiveMask:
    def __init__(self, password=None):
        key = password if password else "default_key"
        self.seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
        self.shift = 4 

    def _zone(self, b):
        """Classifies pixels into protection zones."""
        br = b >> self.shift
        r, g, bl = br[:,:,0], br[:,:,1], br[:,:,2]
        z = np.full((b.shape[0], b.shape[1]), 25, dtype=np.int32)
        z[(g > r) & (g > bl)] = 15 
        z[(g > (100>>self.shift)) & (bl > (100>>self.shift))] = 20
        return z

    def get_score_block(self, block, ch_idx):
        """Deterministic score calculation using float32 for OpenCV compatibility then int32 for symmetry."""
        ch = np.ascontiguousarray(block[:, :, ch_idx])
        s = (ch >> self.shift).astype(np.float32)

        # ── STATS (Use float32 for OpenCV but inputs are discrete) ──
        mean = cv2.boxFilter(s, -1, (3, 3))
        sq_mean = cv2.boxFilter(s**2, -1, (3, 3))
        var = np.maximum(sq_mean - mean**2, 0).astype(np.int32)
        
        gx = cv2.Sobel(s, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(s, cv2.CV_32F, 0, 1, ksize=3)
        grad = (gx**2 + gy**2).astype(np.int32)
        
        # ── SCORING (Back to integer for absolute logic symmetry) ──
        score = self._zone(block)
        score += np.select([var < 10, var < 50], [5, 15], default=25)
        score += np.select([grad < 50, grad < 500], [5, 10], default=20)
        
        if ch_idx == 2: score += 5
        return score.astype(np.float32)
