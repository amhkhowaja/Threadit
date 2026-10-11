from __future__ import annotations


class DomainError(Exception):
    """Base domain error. `status` and `error_type` drive the RFC 9457 envelope."""

    status: int = 500
    error_type: str = "about:blank"
    title: str = "Internal Server Error"
    retryable: bool = False

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DomainError):
    status = 404
    error_type = "https://threadit/errors/not-found"
    title = "Resource not found"


class MaxDepthExceeded(DomainError):
    status = 422
    error_type = "https://threadit/errors/max-depth"
    title = "Reply exceeds maximum depth"


class ParentNotInPostError(DomainError):
    status = 422
    error_type = "https://threadit/errors/parent-mismatch"
    title = "Parent comment does not belong to this post"


class IdempotencyConflictError(DomainError):
    status = 409
    error_type = "https://threadit/errors/idempotency-conflict"
    title = "Idempotency key conflict"


class InvalidCursorError(DomainError):
    status = 400
    error_type = "https://threadit/errors/invalid-cursor"
    title = "Invalid cursor"


class SearchNotAvailableError(DomainError):
    status = 501
    error_type = "https://threadit/errors/search-unavailable"
    title = "Search is not available in this phase"
