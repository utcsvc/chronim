"""Chronim: Control your browser. Directly from Python."""
from pathlib import Path
import sysconfig

from .browser import Browser, AsyncBrowser
from .bridge import ensure_sync_bridge
from .config import get_api_key, generate_api_key, DEFAULT_HOST, DEFAULT_PORT
from .connection import AsyncConnection, SyncConnection
from .exceptions import (ChronimError, ConnectionError, AuthenticationError, ElementNotFoundError,
                         TimeoutError, BrowserError, ProtocolError, ExtensionNotFoundError)

__version__ = "0.1.1"

def extension_path() -> str:
    """Return the installed Chrome extension directory for "Load unpacked"."""
    candidates = (
        Path(__file__).resolve().parent.parent / "extension",
        Path(sysconfig.get_path("data")) / "share" / "chronim" / "extension",
    )
    for candidate in candidates:
        if (candidate / "manifest.json").is_file():
            return str(candidate)
    raise FileNotFoundError("Chronim Chrome extension files are missing from this installation")

def connect(*, api_key=None, host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=15) -> Browser:
    """Start/use the localhost bridge and connect a synchronous Browser client."""
    key = api_key or get_api_key()
    ensure_sync_bridge(key, host, port)
    return Browser(SyncConnection(key, host, port, timeout))

async def connect_async(*, api_key=None, host=DEFAULT_HOST, port=DEFAULT_PORT, timeout=15) -> AsyncBrowser:
    """Start/use the localhost bridge and connect an asynchronous Browser client."""
    from .browser import create_async_browser
    return await create_async_browser(api_key or get_api_key(), host, port, timeout)

__all__ = ["connect", "connect_async", "Browser", "AsyncBrowser", "get_api_key", "generate_api_key",
           "ChronimError", "ConnectionError", "AuthenticationError", "ElementNotFoundError", "TimeoutError",
           "BrowserError", "ProtocolError", "ExtensionNotFoundError", "extension_path", "__version__"]
