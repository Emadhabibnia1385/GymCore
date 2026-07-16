"""Domain exceptions raised by the service layer.

The API layer maps these to HTTP status codes; the web layer maps them
to user-facing Persian error messages. Services never raise HTTPException.
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
