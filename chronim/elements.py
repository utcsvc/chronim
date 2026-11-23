"""Element operations exposed on Browser."""
class Elements:
    def click(self, selector, timeout=10): return self._request("element.click", {"selector": selector, "timeout": timeout})
    def type(self, selector, text): return self._request("element.type", {"selector": selector, "text": text})
    def clear(self, selector): return self._request("element.clear", {"selector": selector})
    def get_text(self, selector): return self._request("element.get_text", {"selector": selector})
    def get_attribute(self, selector, attribute): return self._request("element.get_attribute", {"selector": selector, "attribute": attribute})
    def get_html(self, selector): return self._request("element.get_html", {"selector": selector})
    def get_computed_style(self, selector, property=None):
        return self._request("element.get_style", {"selector": selector, "property": property})
    def set_style(self, selector, property, value):
        return self._request("element.set_style", {"selector": selector, "property": property, "value": value})
    def find(self, selector): return self._request("element.find", {"selector": selector})
    def find_all(self, selector): return self._request("element.find_all", {"selector": selector})
    def exists(self, selector): return self._request("element.exists", {"selector": selector})
    def wait_for_element(self, selector, timeout=10, state="attached", text=None):
        return self._request("element.wait", {"selector": selector, "timeout": timeout, "state": state, "text": text})
