import base64
import os

# 设置 OpenSSL 环境变量，解决 legacy provider 问题
os.environ['CRYPTOGRAPHY_OPENSSL_NO_LEGACY'] = '1'

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def parse_key_b64(key_b64):
    key = base64.b64decode(key_b64)
    if len(key) != 16:
        raise ValueError("AES-128-GCM key must be 16 bytes")
    return key


class AesGcmCipher:
    def __init__(self, key):
        if len(key) != 16:
            raise ValueError("AES-128-GCM key must be 16 bytes")
        self._aesgcm = AESGCM(key)

    def encrypt(self, plaintext, aad=b""):
        nonce = os.urandom(12)
        ct = self._aesgcm.encrypt(nonce, plaintext, aad)
        return nonce + ct

    def decrypt(self, packet, aad=b""):
        if len(packet) < 13:
            raise ValueError("ciphertext packet too short")
        nonce = packet[:12]
        ct = packet[12:]
        return self._aesgcm.decrypt(nonce, ct, aad)

