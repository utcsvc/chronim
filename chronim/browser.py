"""Synchronous and asynchronous browser APIs."""
from __future__ import annotations
import asyncio
from .elements import Elements
from .keyboard import Keyboard
from .mouse import Mouse
from .tabs import Tabs
from .screenshot import Screenshot
from .connection import SyncConnection, AsyncConnection

class Browser(Elements, Keyboard, Mouse, Tabs, Screenshot):
    def __init__(self, connection, tab_id=None): self._connection, self._tab_id = connection, tab_id
    def _request(self, action, payload=None):
        payload = dict(payload or {})
        if self._tab_id is not None: payload["target_tab_id"] = self._tab_id
        return self._connection.request(action, payload)
    def on_tab(self, tab_id):
        if not isinstance(tab_id, int) or isinstance(tab_id, bool) or tab_id < 0: raise ValueError("tab_id must be a non-negative integer")
        return Browser(self._connection, tab_id)
    def open(self, url): return self._request("browser.open", {"url": url})
    def back(self): return self._request("browser.back")
    def forward(self): return self._request("browser.forward")
    def refresh(self): return self._request("browser.refresh")
    def close(self):
        try: return self._request("browser.close")
        finally: self.disconnect()
    def disconnect(self): self._connection.close()
    def title(self): return self._request("browser.title")
    def url(self): return self._request("browser.url")
    def execute_js(self, code): return self._request("browser.execute_js", {"code": code})
    def page_source(self): return self._request("page.source")
    def wait_for_load(self, timeout=30): return self._request("browser.wait_for_load", {"timeout": timeout})
    def sleep(self, seconds):
        if seconds < 0: raise ValueError("seconds must be non-negative")
        return self._request("browser.sleep", {"seconds": seconds})

class AsyncBrowser:
    def __init__(self, connection, tab_id=None): self._connection, self._tab_id = connection, tab_id
    async def _request(self, action, payload=None):
        payload = dict(payload or {})
        if self._tab_id is not None: payload["target_tab_id"] = self._tab_id
        return await self._connection.request(action, payload)
    def on_tab(self, tab_id):
        if not isinstance(tab_id, int) or isinstance(tab_id, bool) or tab_id < 0: raise ValueError("tab_id must be a non-negative integer")
        return AsyncBrowser(self._connection, tab_id)
    async def open(self, url): return await self._request("browser.open", {"url":url})
    async def back(self): return await self._request("browser.back")
    async def forward(self): return await self._request("browser.forward")
    async def refresh(self): return await self._request("browser.refresh")
    async def close(self):
        try: return await self._request("browser.close")
        finally: await self.disconnect()
    async def disconnect(self): await self._connection.close()
    async def title(self): return await self._request("browser.title")
    async def url(self): return await self._request("browser.url")
    async def screenshot(self, path=None):
        result=await self._request("browser.screenshot")
        if path is None: return result
        from .screenshot import save_screenshot_data
        return save_screenshot_data(result, path)
    async def execute_js(self, code): return await self._request("browser.execute_js", {"code":code})
    async def page_source(self): return await self._request("page.source")
    async def wait_for_load(self, timeout=30): return await self._request("browser.wait_for_load", {"timeout":timeout})
    async def sleep(self, seconds): return await self._request("browser.sleep", {"seconds":seconds})
    async def click(self, selector, timeout=10): return await self._request("element.click", {"selector":selector,"timeout":timeout})
    async def type(self, selector, text): return await self._request("element.type", {"selector":selector,"text":text})
    async def clear(self, selector): return await self._request("element.clear", {"selector":selector})
    async def get_text(self, selector): return await self._request("element.get_text", {"selector":selector})
    async def get_attribute(self, selector, attribute): return await self._request("element.get_attribute", {"selector":selector,"attribute":attribute})
    async def get_html(self, selector): return await self._request("element.get_html", {"selector":selector})
    async def get_computed_style(self, selector, property=None): return await self._request("element.get_style", {"selector":selector,"property":property})
    async def set_style(self, selector, property, value): return await self._request("element.set_style", {"selector":selector,"property":property,"value":value})
    async def find(self, selector): return await self._request("element.find", {"selector":selector})
    async def find_all(self, selector): return await self._request("element.find_all", {"selector":selector})
    async def exists(self, selector): return await self._request("element.exists", {"selector":selector})
    async def wait_for_element(self, selector, timeout=10, state="attached", text=None): return await self._request("element.wait", {"selector":selector,"timeout":timeout,"state":state,"text":text})
    async def press(self, key): return await self._request("keyboard.press", {"key":key})
    async def hotkey(self, *keys): return await self._request("keyboard.hotkey", {"keys":list(keys)})
    async def trusted_type(self, text): return await self._request("trusted.type", {"text":str(text)})
    async def scroll(self, x=0, y=0): return await self._request("mouse.scroll", {"x":x,"y":y})
    async def move(self, x, y): return await self._request("mouse.move", {"x":x,"y":y})
    async def trusted_click(self, x, y): return await self._request("trusted.click", {"x":x,"y":y})
    async def new_tab(self, url=None): return await self._request("tabs.new", {"url":url})
    async def close_tab(self, tab_id): return await self._request("tabs.close", {"tab_id":tab_id})
    async def switch_tab(self, tab_id): return await self._request("tabs.switch", {"tab_id":tab_id})
    async def get_tabs(self): return await self._request("tabs.list")
    async def active_tab(self): return await self._request("tabs.active")

async def create_async_browser(api_key, host="127.0.0.1", port=8765, timeout=15):
    from .bridge import ensure_async_bridge
    await ensure_async_bridge(api_key, host, port)
    connection = await AsyncConnection(api_key, host, port, timeout).connect()
    return AsyncBrowser(connection)
