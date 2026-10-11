from __future__ import annotations

import uuid

from fastapi import Header, HTTPException, Request


def require_user_id(request: Request) -> str:
    """userId from the API Gateway JWT authorizer claims (sub). Never from the body (R9).

    API Gateway HTTP API injects verified claims under requestContext.authorizer.jwt.claims.
    In local/dev without the gateway, fall back to the x-user-id header (Floci only).
    """
    scope = request.scope.get("aws.event", {})
    claims = scope.get("requestContext", {}).get("authorizer", {}).get("jwt", {}).get("claims", {})
    sub = claims.get("sub") or request.headers.get("x-user-id")
    if not sub:
        raise HTTPException(status_code=401, detail="missing identity")
    return sub


def require_idempotency_key(idempotency_key: str = Header(alias="Idempotency-Key")) -> str:
    try:
        uuid.UUID(idempotency_key)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail="Idempotency-Key must be a UUID") from exc
    return idempotency_key
