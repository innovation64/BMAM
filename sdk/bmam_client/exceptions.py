"""SDK exceptions."""


class BMAMError(Exception):
    """Base exception for all BMAM SDK errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(BMAMError):
    """Raised when a requested resource is not found (404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class AuthError(BMAMError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)


class ValidationError(BMAMError):
    """Raised when request validation fails (422)."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(message, status_code=422)


class TimeoutError(BMAMError):
    """Raised when a request times out."""

    def __init__(self, message: str = "Request timed out"):
        super().__init__(message, status_code=None)


class ConnectionError(BMAMError):
    """Raised when a connection cannot be established."""

    def __init__(self, message: str = "Connection failed"):
        super().__init__(message, status_code=None)


class RateLimitError(BMAMError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: float | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ServerError(BMAMError):
    """Raised for server-side errors (5xx)."""

    def __init__(self, message: str = "Server error", status_code: int = 500):
        super().__init__(message, status_code=status_code)
