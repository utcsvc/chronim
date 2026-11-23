"""Screenshot helper."""
import base64
from pathlib import Path

def save_screenshot_data(data_url, path):
    if not isinstance(data_url, str) or not data_url.startswith("data:image/png;base64,"):
        raise ValueError("Chrome returned an invalid PNG data URL")
    target = Path(path).expanduser()
    target.write_bytes(base64.b64decode(data_url.partition(",")[2], validate=True))
    return str(target.resolve())

class Screenshot:
    def screenshot(self, path=None):
        result = self._request("browser.screenshot", {})
        return result if path is None else save_screenshot_data(result, path)
