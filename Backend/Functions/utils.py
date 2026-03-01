import hashlib

def get_seed_from_password(password: str) -> int:
    """Consistently derive a 32-bit integer seed from a password string."""
    d = hashlib.sha256(password.encode()).digest()
    return int.from_bytes(d[:4], "big")
