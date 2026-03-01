import numpy as np
import cv2
import hashlib

class AdaptiveMask:
    def __init__(self, password=None):
        key = password if password else "default_key"
        self.seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
        self.max_bits = 2

    def _zone(self, b):
        """Classifies pixels into protection zones (Green/Cyan/Default)."""
        br = b >> self.max_bits
        r, g, b_ch = br[:,:,0], br[:,:,1], br[:,:,2]
        z = np.full((b.shape[0], b.shape[1]), 25, dtype=np.uint8)
        z[(g > r) & (g > b_ch)] = 15 # Green protection
        z[(g > (100>>2)) & (b_ch > (100>>2))] = 20 # Cyan protection
        return z

    def _frequency_score(self, ch):
        h, w = ch.shape
        h8, w8 = (h // 8) * 8, (w // 8) * 8
        if h8 == 0 or w8 == 0: return np.zeros((h, w), dtype=np.float32)
        ch_s = (ch[:h8, :w8] >> self.max_bits).astype(np.float32)
        lap = cv2.Laplacian(ch_s, cv2.CV_32F, ksize=3)
        eng = cv2.boxFilter(np.abs(lap), -1, (8, 8))
        res = np.zeros((h, w), dtype=np.float32)
        res[:h8, :w8] = eng
        return (res / 2500.0) * 50

    def get_score_block(self, block, ch_idx):
        """Calculates complexity score: Zone + Variance + Gradient + Frequency."""
        b_cont = np.ascontiguousarray(block)
        ch = np.ascontiguousarray(b_cont[:, :, ch_idx])
        s = (ch >> self.max_bits).astype(np.float32)

        # ── STATS ──
        mean = cv2.boxFilter(s, -1, (3, 3))
        sq_mean = cv2.boxFilter(s**2, -1, (3, 3))
        var = np.maximum(sq_mean - mean**2, 0)
        grad = cv2.Sobel(s, cv2.CV_32F, 1, 0)**2 + cv2.Sobel(s, cv2.CV_32F, 0, 1)**2
        
        # ── SCORING ──
        score = self._zone(b_cont).astype(np.float32)
        score += np.select([var < 225, var < 900], [5, 15], default=25)
        score += np.select([grad < 100, grad < 900], [5, 10], default=20)
        score += self._frequency_score(ch)
        
        if ch_idx == 2: score += 5
        return score
