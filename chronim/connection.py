"""Authenticated request/response WebSocket clients (sync and async)."""
from __future__ import annotations
import asyncio, threading, uuid
from typing import Any
import websockets
from .exceptions import AuthenticationError, ConnectionError, ProtocolError, TimeoutError
from .protocol import dumps, loads, request

class AsyncConnection:
    def __init__(self, api_key: str, host: str = "127.0.0.1", port: int = 8765, timeout: float = 15):
        self.api_key, self.uri, self.timeout = api_key, f"ws://{host}:{port}", timeout
        self.ws = None; self._pending: dict[str, asyncio.Future] = {}; self._reader = None; self._send_lock = asyncio.Lock()
    async def connect(self):
        try:
            self.ws = await websockets.connect(self.uri, max_size=16*1024*1024, open_timeout=self.timeout)
            await self.ws.send(dumps({"type":"hello","role":"client","token":self.api_key}))
            auth = loads(await asyncio.wait_for(self.ws.recv(), self.timeout))
            if not auth.get("success"):
                raise AuthenticationError((auth.get("error") or {}).get("message", "Chronim authentication failed"))
            self._reader = asyncio.create_task(self._read_loop())
            return self
        except AuthenticationError: raise
        except Exception as exc: raise ConnectionError(f"Could not connect to Chronim bridge at {self.uri}: {exc}") from exc
    async def _read_loop(self):
        try:
            async for raw in self.ws:
                msg = loads(raw); rid = msg.get("id"); future = self._pending.get(rid)
                if future and not future.done(): future.set_result(msg)
        except Exception as exc:
            for f in self._pending.values():
                if not f.done(): f.set_exception(ConnectionError(f"Chronim bridge disconnected: {exc}"))
        else:
            for f in self._pending.values():
                if not f.done(): f.set_exception(ConnectionError("Chronim bridge closed the connection"))
    async def request(self, action: str, payload: dict[str, Any] | None = None):
        if not self.ws: raise ConnectionError("Not connected to Chronim bridge")
        msg = request(action, payload); rid = msg["id"]; future = asyncio.get_running_loop().create_future(); self._pending[rid] = future
        try:
            async with self._send_lock: await self.ws.send(dumps(msg))
            try: response = await asyncio.wait_for(future, self.timeout)
            except asyncio.TimeoutError as exc: raise TimeoutError(f"Chronim request {action} timed out after {self.timeout:g}s") from exc
            if not response.get("success"):
                error = response.get("error") or {}; code, text = error.get("code"), error.get("message", "Chrome command failed")
                if code == "ELEMENT_NOT_FOUND":
                    from .exceptions import ElementNotFoundError
                    raise ElementNotFoundError(text)
                if code == "TIMEOUT": raise TimeoutError(text)
                if code == "EXTENSION_NOT_FOUND":
                    from .exceptions import ExtensionNotFoundError
                    raise ExtensionNotFoundError(text)
                if code == "PROTOCOL_ERROR": raise ProtocolError(text)
                if code == "CONNECTION_ERROR": raise ConnectionError(text)
                from .exceptions import BrowserError
                raise BrowserError(text)
            return response.get("result")
        finally: self._pending.pop(rid, None)
    async def close(self):
        if self.ws:
            await self.ws.close(); self.ws = None
        if self._reader:
            self._reader.cancel(); self._reader = None

class SyncConnection:
    def __init__(self, api_key: str, host: str = "127.0.0.1", port: int = 8765, timeout: float = 15):
        self.loop = asyncio.new_event_loop(); self.ready = threading.Event(); self.error = None
        self.thread = threading.Thread(target=self._run, daemon=True, name="chronim-client"); self.thread.start()
        self.conn = AsyncConnection(api_key, host, port, timeout)
        fut = asyncio.run_coroutine_threadsafe(self.conn.connect(), self.loop)
        try: fut.result(timeout + 3)
        except Exception as exc:
            self.loop.call_soon_threadsafe(self.loop.stop)
            raise exc
    def _run(self):
        asyncio.set_event_loop(self.loop); self.loop.run_forever()
    def request(self, action, payload=None):
        return asyncio.run_coroutine_threadsafe(self.conn.request(action, payload), self.loop).result(self.conn.timeout + 2)
    def close(self):
        if self.conn.ws:
            asyncio.run_coroutine_threadsafe(self.conn.close(), self.loop).result(3)
        self.loop.call_soon_threadsafe(self.loop.stop)
