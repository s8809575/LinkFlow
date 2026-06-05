import base64
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python", "linkflow"))


class TestRpcCrypto(unittest.TestCase):
    def test_aes_gcm_roundtrip(self):
        from core.rpc_crypto import AesGcmCipher

        key = os.urandom(16)
        cipher = AesGcmCipher(key)

        plaintext = b'{"jsonrpc":"2.0","method":"ping"}'
        packet = cipher.encrypt(plaintext)
        out = cipher.decrypt(packet)
        self.assertEqual(out, plaintext)

    def test_key_b64_parse(self):
        from core.rpc_crypto import parse_key_b64

        key = os.urandom(16)
        b64 = base64.b64encode(key).decode("ascii")
        self.assertEqual(parse_key_b64(b64), key)

