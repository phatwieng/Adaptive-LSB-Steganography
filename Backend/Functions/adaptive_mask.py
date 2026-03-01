import numpy as np
import cv2
import hashlib

class AdaptiveMask:
    def __init__(self, password=None):
        key = password if password else "default_key"
        self.seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
        # Shift 4: analyze only high-order bits for 100% LSB immunity
        self.shift = 4 

    def get_score_block(self, block, ch_idx):
        """Calculates integer-based complexity score for platform consistency."""
        b = np.ascontiguousarray(block)
        ch = np.ascontiguousarray(b[:, :, ch_idx])
        s = (ch >> self.shift).astype(np.int32)

        # ── SPATIAL VARIANCE (Integer) ──
        mean = cv2.boxFilter(s, cv2.CV_32S, (3, 3))
        sq_mean = cv2.boxFilter(s**2, cv2.CV_32S, (3, 3))
        var = np.maximum(sq_mean - mean**2, 0)

        # ── EDGES (Integer) ──
        gx = cv2.Sobel(s, cv2.CV_32S, 1, 0, ksize=3)
        gy = cv2.Sobel(s, cv2.CV_32S, 0, 1, ksize=3)
        grad = gx**2 + gy**2
        
        # ── SCORING (Deterministic Integers) ──
        score = np.full(ch.shape, 20, dtype=np.int32)
        score += np.select([var < 10, var < 50], [5, 15], default=25)
        score += np.select([grad < 50, grad < 500], [5, 10], default=20)
        
        if ch_idx == 2: score += 5
        return score.astype(np.float32)
