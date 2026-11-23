import unittest
from chronim.protocol import dumps, loads, request, validate_request
from chronim.exceptions import ProtocolError

class ProtocolTests(unittest.TestCase):
    def test_request_round_trip(self):
        original = request("browser.open", {"url": "https://example.com"}, "req-1")
        decoded = loads(dumps(original))
        validate_request(decoded)
        self.assertEqual(decoded, original)

    def test_rejects_non_object(self):
        with self.assertRaises(ProtocolError):
            loads("[]")

    def test_rejects_invalid_request(self):
        with self.assertRaises(ProtocolError):
            validate_request({"id": 3, "action": "browser.open"})

if __name__ == "__main__": unittest.main()
