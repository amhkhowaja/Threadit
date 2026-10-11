from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def install_cors(app: FastAPI, allow_origins: str) -> None:
    origins = [o.strip() for o in allow_origins.split(",") if o.strip()]
    if not origins:
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "x-user-id"],
        max_age=600,
    )
