"""Public exception hierarchy for Chronim."""

class ChronimError(Exception):
    """Base class for errors raised by Chronim."""

class ConnectionError(ChronimError):
    """The local bridge could not be reached or disconnected."""
    code = "CONNECTION_ERROR"

class AuthenticationError(ConnectionError):
    """The bridge rejected the configured API key."""
    code = "AUTHENTICATION_FAILED"

class ElementNotFoundError(ChronimError):
    """A selector did not match an element."""
    code = "ELEMENT_NOT_FOUND"

class TimeoutError(ChronimError):
    """An operation did not complete before its timeout."""
    code = "TIMEOUT"

class BrowserError(ChronimError):
    """Chrome could not perform the requested operation."""
    code = "BROWSER_ERROR"

class ProtocolError(ChronimError):
    """A peer sent an invalid or unsupported protocol message."""
    code = "PROTOCOL_ERROR"

class ExtensionNotFoundError(ConnectionError):
    """No authenticated Chronim extension is connected."""
    code = "EXTENSION_NOT_FOUND"
