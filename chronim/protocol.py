"""JSON protocol validation and message constructors."""
from __future__ import annotations
import json, uuid
from typing import Any
from .exceptions import ProtocolError

MAX_MESSAGE_BYTES = 16 * 1024 * 1024

def request(action: str, payload: dict[str, Any] | None = None, request_id: str | None = None) -> dict[str, Any]:
    if not isinstance(action, str) or not action:
        raise ProtocolError("Action must be a non-empty string")
    return {"type": "request", "id": request_id or uuid.uuid4().hex, "action": action, "payload": payload or {}}

def dumps(message: dict[str, Any]) -> str:
    try:
        result = json.dumps(message, separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"Message cannot be encoded as JSON: {exc}") from exc
    if len(result.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Message exceeds the 16 MiB protocol limit")
    return result

def loads(raw: str | bytes) -> dict[str, Any]:
    if isinstance(raw, bytes):
        if len(raw) > MAX_MESSAGE_BYTES:
            raise ProtocolError("Message exceeds the 16 MiB protocol limit")
        raw = raw.decode("utf-8")
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ProtocolError("Invalid or oversized message")
    try:
        value = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProtocolError("Message is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ProtocolError("Protocol message must be a JSON object")
    return value

def validate_request(message: dict[str, Any]) -> None:
    if message.get("type") != "request" or not isinstance(message.get("id"), str) or not isinstance(message.get("action"), str) or not isinstance(message.get("payload", {}), dict):
        raise ProtocolError("Expected a request with string id/action and object payload")
