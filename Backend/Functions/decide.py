import numpy as np
from .adaptive_mask import AdaptiveMask

class AdaptiveLSBCore:
    def __init__(self, password=None, block_rows=512):
        self.masker = AdaptiveMask(password)
        self.block_rows = block_rows

    def _get_best_threshold(self, img, bit_len, forbidden_indices=None):
        thresholds = [55, 45, 35, 25, 15, 5]
        bits_per_t = {t: 0 for t in thresholds}
        rows, cols, ch = img.shape
        # Speed optimization: Sample every 4th block for huge images (>16k)
        step = 4 if rows > 16384 else 1
        
        for rs in range(0, rows, self.block_rows * step):
            re = min(rs + self.block_rows, rows)
            block = img[rs:re]
            for c in range(ch):
                score = self.masker.get_score_block(block, c).ravel()
                for t in thresholds:
                    mask = score >= t
                    bits_per_t[t] += np.sum(np.where(score[mask] >= 70, 2, 1))
        
        # Scale back up if we sampled
        if step > 1:
            for t in thresholds: bits_per_t[t] *= step

        if forbidden_indices:
            for t in thresholds: bits_per_t[t] -= len(forbidden_indices)
        for t in thresholds:
            if bits_per_t[t] >= bit_len: return t
        return thresholds[-1]

    def calculate_capacity(self, img, threshold=35):
        rows, cols, ch = img.shape
        total = 0
        step = 4 if rows > 16384 else 1
        for rs in range(0, rows, self.block_rows * step):
            re = min(rs + self.block_rows, rows)
            block = img[rs:re]
            for c in range(ch):
                score = self.masker.get_score_block(block, c).ravel()
                mask = score >= threshold
                total += np.sum(np.where(score[mask] >= 70, 2, 1))
        return int(total * step)

    def _get_shuffled_indices(self, size, seed):
        """Standardized LCG-based shuffle for absolute symmetry."""
        indices = np.arange(size, dtype=np.int32)
        a, c, m = 1664525, 1013904223, 2**32
        curr = seed
        for i in range(size - 1, 0, -1):
            curr = (a * curr + c) % m
            j = curr % (i + 1)
            indices[i], indices[j] = indices[j], indices[i]
        return indices

    def encode(self, img, byte_payload, forbidden_indices=None):
        rows, cols, ch = img.shape
        bit_payload = np.unpackbits(np.frombuffer(byte_payload, dtype=np.uint8))
        bit_len, bit_idx = len(bit_payload), 0
        threshold = self._get_best_threshold(img, bit_len, forbidden_indices)
        forbidden_set = set(forbidden_indices) if forbidden_indices else set()

        for rs in range(0, rows, self.block_rows):
            re = min(rs + self.block_rows, rows)
            block, b_start = img[rs:re], rs * cols * ch
            for c in range(ch):
                score = self.masker.get_score_block(block, c).ravel()
                l_indices = np.flatnonzero(score >= threshold)
                if l_indices.size == 0: continue
                
                # Use LCG shuffle
                shuffled_map = self._get_shuffled_indices(len(l_indices), b_start + c)
                l_indices = l_indices[shuffled_map]

                for l_idx in l_indices:
                    g_idx = b_start + c + (l_idx * ch)
                    if g_idx in forbidden_set: continue
                    r, cl = l_idx // cols, l_idx % cols
                    bits = 2 if score[l_idx] >= 70 else 1
                    bits = min(bits, bit_len - bit_idx)
                    if bits == 1:
                        block[r, cl, c] = (block[r, cl, c] & 0xFE) | bit_payload[bit_idx]
                        bit_idx += 1
                    else:
                        block[r, cl, c] = (block[r, cl, c] & 0xFC) | (bit_payload[bit_idx] << 1 | bit_payload[bit_idx+1])
                        bit_idx += 2
                    if bit_idx >= bit_len: return img
        return img

    def decode(self, img, bit_len, forbidden_indices=None):
        rows, cols, ch = img.shape
        bit_payload = np.zeros(bit_len, dtype=np.uint8)
        bit_idx, threshold = 0, self._get_best_threshold(img, bit_len, forbidden_indices)
        forbidden_set = set(forbidden_indices) if forbidden_indices else set()

        for rs in range(0, rows, self.block_rows):
            re = min(rs + self.block_rows, rows)
            block, b_start = img[rs:re], rs * cols * ch
            for c in range(ch):
                score = self.masker.get_score_block(block, c).ravel()
                l_indices = np.flatnonzero(score >= threshold)
                if l_indices.size == 0: continue
                
                shuffled_map = self._get_shuffled_indices(len(l_indices), b_start + c)
                l_indices = l_indices[shuffled_map]

                for l_idx in l_indices:
                    g_idx = b_start + c + (l_idx * ch)
                    if g_idx in forbidden_set: continue
                    r, cl = l_idx // cols, l_idx % cols
                    bits = 2 if score[l_idx] >= 70 else 1
                    bits = min(bits, bit_len - bit_idx)
                    
                    if bits == 1:
                        bit_payload[bit_idx] = img[rs + r, cl, c] & 1
                        bit_idx += 1
                    else:
                        v = img[rs + r, cl, c]
                        bit_payload[bit_idx] = (v >> 1) & 1
                        bit_payload[bit_idx+1] = v & 1
                        bit_idx += 2
                    if bit_idx >= bit_len: return np.packbits(bit_payload).tobytes()
        return np.packbits(bit_payload).tobytes()
