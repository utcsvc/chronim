"""Mouse operations exposed on Browser."""
class Mouse:
    def scroll(self, x=0, y=0): return self._request("mouse.scroll", {"x": x, "y": y})
    def move(self, x, y): return self._request("mouse.move", {"x": x, "y": y})
    def trusted_click(self, x, y): return self._request("trusted.click", {"x": x, "y": y})
