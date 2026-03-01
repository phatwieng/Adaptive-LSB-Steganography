from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Random import get_random_bytes
import base64

class SecureAESCipher:
    
    def __init__(self, password):
        self.password = password

    def encrypt(self, plaintext):
        # Generate a random 16-byte salt for EACH encryption
        salt = get_random_bytes(16)
        # Derive key using the unique salt
        key = PBKDF2(self.password, salt, dkLen=32, count=100000)
        
        cipher = AES.new(key, AES.MODE_GCM, nonce=get_random_bytes(12))
        ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode('utf-8'))
        
        # Return format: SALT (16) + NONCE (12) + TAG (16) + CIPHERTEXT
        return salt + cipher.nonce + tag + ciphertext

    def decrypt(self, data: bytes):
        try:
            # Extract components
            salt = data[:16]
            nonce = data[16:28]
            tag = data[28:44]
            ciphertext = data[44:]

            # Re-derive key using the extracted salt
            key = PBKDF2(self.password, salt, dkLen=32, count=100000)

            cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
            decrypted_data = cipher.decrypt_and_verify(ciphertext, tag)
            return decrypted_data.decode('utf-8')

        except (ValueError, KeyError, UnicodeDecodeError) as e:
            return f"Error: Incorrect password or corrupted data - {str(e)}"
