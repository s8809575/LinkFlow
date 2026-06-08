import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "python", "linkflow"))


class TestMdnsService(unittest.TestCase):
    def test_build_service_name(self):
        from core.mdns_service import MdnsService

        s = MdnsService(service_name="LinkFlow", port=8089, properties={"pairing_id": "p1"})
        self.assertIn("_companion._tcp.local.", s.service_type)

