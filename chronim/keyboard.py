"""Keyboard operations exposed on Browser."""
class Keyboard:
    def press(self, key): return self._request("keyboard.press", {"key": key})
    def hotkey(self, *keys): return self._request("keyboard.hotkey", {"keys": list(keys)})
    def trusted_type(self, text): return self._request("trusted.type", {"text": str(text)})
