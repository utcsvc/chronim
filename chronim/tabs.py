"""Tab operations exposed on Browser."""
class Tabs:
    def new_tab(self, url=None): return self._request("tabs.new", {"url": url})
    def close_tab(self, tab_id): return self._request("tabs.close", {"tab_id": tab_id})
    def switch_tab(self, tab_id): return self._request("tabs.switch", {"tab_id": tab_id})
    def get_tabs(self): return self._request("tabs.list", {})
    def active_tab(self): return self._request("tabs.active", {})
