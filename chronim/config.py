"""Configuration helpers. Secrets are stored with restrictive permissions where supported."""
from __future__ import annotations
import json, os, secrets
from pathlib import Path
from .exceptions import ChronimError

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_TIMEOUT = 15.0

def config_path() -> Path:
    base = Path(os.environ.get("APPDATA") or (Path.home() / ".config"))
    return base / "chronim" / "config.json"

def get_api_key() -> str:
    """Return CHRONIM_API_KEY or create/read a per-user local key."""
    env = os.environ.get("CHRONIM_API_KEY")
    if env:
        if len(env) < 32:
            raise ChronimError("CHRONIM_API_KEY must contain at least 32 characters")
        return env
    path = config_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            key = data.get("api_key")
            if isinstance(key, str) and len(key) >= 32:
                return key
            raise ChronimError(f"Invalid Chronim key configuration: {path}")
        key = secrets.token_urlsafe(32)
        path.write_text(json.dumps({"api_key": key}, indent=2), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return key
    except ChronimError:
        raise
    except (OSError, ValueError) as exc:
        raise ChronimError(f"Could not read or create Chronim configuration at {path}: {exc}") from exc

def generate_api_key() -> str:
    """Generate a cryptographically secure key suitable for CHRONIM_API_KEY."""
    return secrets.token_urlsafe(32)
