import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "python", "linkflow"))


class TestRpcFramer(unittest.TestCase):
    def test_frame_roundtrip_plain(self):
        from core.rpc_framer import LengthPrefixedFramer

        framer = LengthPrefixedFramer()
        msg = b"hello"
        framed = framer.pack(msg)
        self.assertEqual(framer.unpack_from_buffer(framed)[0], msg)

    def test_frame_roundtrip_encrypted(self):
        from core.rpc_crypto import AesGcmCipher
        from core.rpc_framer import LengthPrefixedFramer

        cipher = AesGcmCipher(os.urandom(16))
        framer = LengthPrefixedFramer(cipher=cipher)

        msg = b'{"jsonrpc":"2.0","method":"ping"}'
        framed = framer.pack(msg)
        out, rest = framer.unpack_from_buffer(framed)
        self.assertEqual(rest, b"")
        self.assertEqual(out, msg)

