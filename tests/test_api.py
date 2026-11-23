import asyncio
import unittest
import chronim
from chronim.browser import Browser, AsyncBrowser

class FakeSyncConnection:
    def __init__(self): self.calls=[]; self.closed=False
    def request(self, action, payload=None): self.calls.append((action,payload)); return "ok"
    def close(self): self.closed=True

class FakeAsyncConnection:
    def __init__(self): self.calls=[]; self.closed=False
    async def request(self, action, payload=None): self.calls.append((action,payload)); return "ok"
    async def close(self): self.closed=True

class ApiTests(unittest.TestCase):
    def test_public_api_and_sync_dispatch(self):
        connection=FakeSyncConnection(); browser=Browser(connection)
        self.assertEqual(browser.open("https://example.com"), "ok")
        self.assertEqual(connection.calls[-1], ("browser.open", {"url":"https://example.com"}))
        self.assertTrue(hasattr(chronim,"connect_async"))

    def test_async_dispatch(self):
        async def run():
            connection=FakeAsyncConnection(); browser=AsyncBrowser(connection)
            self.assertEqual(await browser.click("#go"), "ok")
            self.assertEqual(connection.calls[-1], ("element.click", {"selector":"#go"}))
        asyncio.run(run())

if __name__ == "__main__": unittest.main()
