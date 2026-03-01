import numpy as np

class HammingCode:
    """
    Highly optimized Hamming(7,4) implementation using NumPy vectorization.
    Overhead: 2x (4 data bits -> 8 encoded bits)
    """
    def encode(self, data: bytes) -> bytes:
        if not data: return b""
        
        # 1. Convert bytes to bits
        arr = np.frombuffer(data, dtype=np.uint8)
        # Split each byte into high and low nibbles
        nibbles = np.zeros(len(arr) * 2, dtype=np.uint8)
        nibbles[0::2] = (arr >> 4) & 0xF
        nibbles[1::2] = arr & 0xF
        
        # 2. Extract bits from nibbles (shape: N*2, 4)
        bits = np.unpackbits(nibbles.reshape(-1, 1), axis=1)[:, 4:]
        d1, d2, d3, d4 = bits[:, 0], bits[:, 1], bits[:, 2], bits[:, 3]
        
        # 3. Calculate parity bits (vectorized XOR)
        p1 = d1 ^ d2 ^ d4
        p2 = d1 ^ d3 ^ d4
        p3 = d2 ^ d3 ^ d4
        
        # 4. Construct 7-bit codewords
        # Order: p1 p2 d1 p3 d2 d3 d4
        res = (p1 << 7) | (p2 << 6) | (d1 << 5) | (p3 << 4) | (d2 << 3) | (d3 << 2) | (d4 << 1)
        
        # 5. Calculate overall parity p4 for 8-bit codeword
        p4 = np.zeros_like(res)
        for k in range(1, 8):
            p4 ^= (res >> k) & 1
        
        return bytes(res | p4)

    def decode(self, data: bytes) -> bytes:
        if not data: return b""
        
        # 1. Load data into numpy
        v = np.frombuffer(data, dtype=np.uint8)
        
        # 2. Extract bits for syndrome calculation
        p1 = (v >> 7) & 1
        p2 = (v >> 6) & 1
        d1 = (v >> 5) & 1
        p3 = (v >> 4) & 1
        d2 = (v >> 3) & 1
        d3 = (v >> 2) & 1
        d4 = (v >> 1) & 1
        
        # 3. Calculate syndrome
        s1 = p1 ^ d1 ^ d2 ^ d4
        s2 = p2 ^ d1 ^ d3 ^ d4
        s3 = p3 ^ d2 ^ d3 ^ d4
        syndrome = (s3 << 2) | (s2 << 1) | s1
        
        # 4. Vectorized error correction
        # Correction logic: flip bit if syndrome matches
        d1 ^= (syndrome == 3).astype(np.uint8)
        d2 ^= (syndrome == 5).astype(np.uint8)
        d3 ^= (syndrome == 6).astype(np.uint8)
        d4 ^= (syndrome == 7).astype(np.uint8)
        
        # 5. Reconstruct nibbles
        nibbles = (d1 << 3) | (d2 << 2) | (d3 << 1) | d4
        
        # 6. Reconstruct bytes from high/low nibbles
        high = nibbles[0::2]
        low = nibbles[1::2]
        
        return bytes((high << 4) | low)
