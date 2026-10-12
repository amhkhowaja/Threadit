from __future__ import annotations

import uuid

from fastapi import Header, HTTPException, Request

from threadit_core.api.jwt_verify import verify_bearer


def require_user_id(request: Request) -> str:
    """Resolve the caller's userId (never from the body, R9), in priority order:
    1. A verified Cognito Bearer token (prod: in-service JWT verification).
    2. API Gateway JWT authorizer claims (if fronted by API GW).
    3. x-user-id header (local/dev fallback only).
    """
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        sub = verify_bearer(auth[7:].strip())
        if sub:
            return sub
        raise HTTPException(status_code=401, detail="invalid token")

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
