"""Authenticated localhost WebSocket server that routes requests to the extension."""
from __future__ import annotations
import asyncio, hmac, logging, re, threading
from typing import Any
import websockets
from websockets.exceptions import ConnectionClosed
from .config import DEFAULT_HOST, DEFAULT_PORT
from .exceptions import (AuthenticationError, BrowserError, ElementNotFoundError,
                         ExtensionNotFoundError, ProtocolError, TimeoutError)
from .protocol import dumps, loads, validate_request

logger = logging.getLogger("chronim")
_ALLOWED_ROLES = {"extension", "client"}

class Bridge:
    def __init__(self, api_key: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, request_timeout: float = 30):
        self.api_key, self.host, self.port, self.request_timeout = api_key, host, port, request_timeout
        self._extension = None
        self._pending: dict[str, asyncio.Future] = {}
        self._server = None
        self._lock = asyncio.Lock()

    async def start(self):
        try:
            self._server = await websockets.serve(self._handler, self.host, self.port, max_size=16*1024*1024, ping_interval=20, ping_timeout=20)
        except OSError as exc:
            raise RuntimeError(f"Could not start Chronim bridge at {self.host}:{self.port}: {exc}") from exc

    async def close(self):
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        if self._extension:
            await self._extension.close()

    async def _handler(self, ws):
        remote = ws.remote_address
        if not remote or remote[0] not in ("127.0.0.1", "::1", "::ffff:127.0.0.1"):
            await ws.close(code=1008, reason="localhost only")
            return
        headers = getattr(ws, "request_headers", None)
        if headers is None:
            headers = ws.request.headers
        origin = headers.get("Origin", "")
        if origin and not re.fullmatch(r"chrome-extension://[a-p]{32}", origin):
            await ws.close(code=1008, reason="invalid origin")
            return
        try:
            hello = loads(await asyncio.wait_for(ws.recv(), 5))
            role = hello.get("role")
            supplied = hello.get("token")
            if role not in _ALLOWED_ROLES or not isinstance(supplied, str) or not hmac.compare_digest(supplied, self.api_key):
                await ws.send(dumps({"type":"auth","success":False,"error":{"code":"AUTHENTICATION_FAILED","message":"Invalid Chronim API key"}}))
                await ws.close(code=1008, reason="authentication failed")
                return
            await ws.send(dumps({"type":"auth","success":True,"role":role}))
            if role == "extension":
                await self._extension_loop(ws)
            else:
                await self._client_loop(ws)
        except (asyncio.TimeoutError, ProtocolError, ConnectionClosed):
            await ws.close(code=1002, reason="invalid handshake or protocol")

    async def _extension_loop(self, ws):
        old = self._extension
        self._extension = ws
        if old and old != ws:
            await old.close()
        logger.info("Chronim extension connected")
        try:
            async for raw in ws:
                msg = loads(raw)
                if msg.get("type") == "response" and isinstance(msg.get("id"), str):
                    future = self._pending.get(msg["id"])
                    if future and not future.done(): future.set_result(msg)
        finally:
            if self._extension is ws: self._extension = None
            for future in self._pending.values():
                if not future.done(): future.set_exception(ExtensionNotFoundError("Chronim extension disconnected"))
            logger.info("Chronim extension disconnected")

    async def _client_loop(self, ws):
        async for raw in ws:
            msg = {}
            try:
                msg = loads(raw); validate_request(msg)
                result = await self.dispatch(msg["action"], msg.get("payload", {}), msg["id"])
                response = {"type":"response","id":msg["id"],"success":True,"result":result}
            except Exception as exc:
                response = {"type":"response","id":msg.get("id", ""),"success":False,"error":{"code":getattr(exc,"code","BROWSER_ERROR"),"message":str(exc)}}
            await ws.send(dumps(response))

    async def dispatch(self, action: str, payload: dict[str, Any], request_id: str | None = None):
        if not self._extension:
            raise ExtensionNotFoundError("Chronim extension is not connected. Open the extension popup and connect it.")
        rid = request_id or __import__("uuid").uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self._pending[rid] = future
        try:
            await self._extension.send(dumps({"type":"request","id":rid,"action":action,"payload":payload}))
            try: response = await asyncio.wait_for(future, self.request_timeout)
            except asyncio.TimeoutError as exc: raise TimeoutError(f"Timed out waiting for {action} after {self.request_timeout:g}s") from exc
            if not response.get("success"):
                err = response.get("error") or {}
                message = err.get("message", "Chrome command failed")
                code = err.get("code")
                if code == "PROTOCOL_ERROR": raise ProtocolError(message)
                if code == "ELEMENT_NOT_FOUND": raise ElementNotFoundError(message)
                if code == "TIMEOUT": raise TimeoutError(message)
                raise BrowserError(message)
            return response.get("result")
        finally:
            self._pending.pop(rid, None)

class _BridgeThread:
    """Own a bridge in a daemon event-loop thread for the synchronous API."""
    def __init__(self, api_key: str, host: str, port: int):
        self.loop = asyncio.new_event_loop(); self.bridge = Bridge(api_key, host, port)
        self.ready = threading.Event(); self.error = None
        self.thread = threading.Thread(target=self._run, name="chronim-bridge", daemon=True)
        self.thread.start()
        self.loop.call_soon_threadsafe(self._start)
        if not self.ready.wait(5): raise RuntimeError("Chronim bridge startup timed out")
        if self.error: raise self.error
    def _run(self):
        asyncio.set_event_loop(self.loop); self.loop.run_forever()
    def _start(self):
        task = self.loop.create_task(self.bridge.start())
        task.add_done_callback(self._started)
    def _started(self, task):
        try: task.result()
        except Exception as exc: self.error = exc
        self.ready.set()

_sync_lock = threading.Lock()
_sync_bridge: _BridgeThread | None = None
_async_bridges: dict[tuple[str,int,str], Bridge] = {}

def ensure_sync_bridge(api_key: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    global _sync_bridge
    with _sync_lock:
        if _sync_bridge is not None:
            bridge = _sync_bridge.bridge
            if (bridge.api_key, bridge.host, bridge.port) != (api_key, host, port):
                raise RuntimeError("A Chronim bridge is already running with a different key or port")
            return
        if _sync_bridge is None:
            _sync_bridge = _BridgeThread(api_key, host, port)

async def ensure_async_bridge(api_key: str, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    # Keep the listener alive beyond the caller's event loop (including asyncio.run()).
    ensure_sync_bridge(api_key, host, port)
    return _sync_bridge.bridge
