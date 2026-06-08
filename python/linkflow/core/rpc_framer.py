import struct


class LengthPrefixedFramer:
    def __init__(self, cipher=None):
        self._cipher = cipher

    def pack(self, payload):
        if self._cipher:
            payload = self._cipher.encrypt(payload)
        return struct.pack("!I", len(payload)) + payload

    def unpack_from_buffer(self, buf):
        if len(buf) < 4:
            return None, buf
        (n,) = struct.unpack("!I", buf[:4])
        if n < 0:
            raise ValueError("negative frame length")
        if len(buf) < 4 + n:
            return None, buf
        body = buf[4 : 4 + n]
        rest = buf[4 + n :]
        if self._cipher:
            body = self._cipher.decrypt(body)
        return body, rest

