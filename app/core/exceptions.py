"""Domain exceptions raised by the service layer.

Services never raise HTTP or platform-specific errors. Bot handlers catch
`DomainError` and show its (Persian) message; the internal API maps them to
status codes.
"""


class DomainError(Exception):
    """Base class — a business rule was violated."""


class NotFoundError(DomainError):
    """Requested entity does not exist."""


class ValidationError(DomainError):
    """Input is invalid for the requested operation."""


class AuthError(DomainError):
    """Authentication or authorization failed."""


class ConflictError(DomainError):
    """Operation conflicts with existing state (e.g. duplicate phone)."""
