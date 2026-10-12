from __future__ import annotations

import threading

import jwt
from jwt import PyJWKClient

# Verifies Cognito access/id tokens via the pool JWKS. Configured from env; when unset,
# the service falls back to the dev x-user-id header (local/Floci only).


class CognitoVerifier:
    def __init__(self, issuer: str, audience: str | None) -> None:
        self._issuer = issuer.rstrip("/")
        self._client_id = audience or None  # Cognito app client id
        self._jwks = PyJWKClient(f"{self._issuer}/.well-known/jwks.json")

    def verify_sub(self, token: str) -> str | None:
        try:
            key = self._jwks.get_signing_key_from_jwt(token).key
            # Cognito ACCESS tokens have no `aud` (they carry `client_id` + token_use=access);
            # ID tokens have `aud`. Verify signature/issuer/exp here and check client_id below,
            # so both token types work without a false `aud` failure.
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"verify_aud": False},
            )
        except Exception:  # noqa: BLE001 - any verification failure => unauthenticated
            return None
        if self._client_id:
            allowed = {claims.get("client_id"), claims.get("aud")}
            if self._client_id not in allowed:
                return None
        return claims.get("sub")


_verifier: CognitoVerifier | None = None
_lock = threading.Lock()


def configure_verifier(issuer: str, audience: str | None) -> None:
    global _verifier
    with _lock:
        _verifier = CognitoVerifier(issuer, audience) if issuer else None


def verify_bearer(token: str) -> str | None:
    v = _verifier
    return v.verify_sub(token) if v else None
