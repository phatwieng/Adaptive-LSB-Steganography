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
        """Calculates complexity score: Zone + Variance + Gradient + Frequency."""
        b = np.ascontiguousarray(block)
        ch = np.ascontiguousarray(b[:, :, ch_idx])
        s = (ch >> self.shift).astype(np.float32)

        # ── SPATIAL VARIANCE ──
        mean = cv2.boxFilter(s, -1, (3, 3))
        sq_mean = cv2.boxFilter(s**2, -1, (3, 3))
        var = np.maximum(sq_mean - mean**2, 0)

        # ── EDGES ──
        gx = cv2.Sobel(s, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(s, cv2.CV_32F, 0, 1, ksize=3)
        grad = gx**2 + gy**2

        # ── SCORING ──
        # Cast back to int32 for deterministic selective logic
        v_int = var.astype(np.int32)
        g_int = grad.astype(np.int32)

        score = np.full(ch.shape, 20, dtype=np.int32)
        score += np.select([v_int < 10, v_int < 50], [5, 15], default=25)
        score += np.select([g_int < 50, g_int < 500], [5, 10], default=20)

        if ch_idx == 2: score += 5
        return score.astype(np.float32)
