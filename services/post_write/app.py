from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from threadit_core.api.cors import install_cors
from threadit_core.api.dtos import (
    CommentResponse,
    CreateCommentRequest,
    CreatePostRequest,
    PostResponse,
    PresignRequest,
    PresignResponse,
)
from threadit_core.api.errors import install_error_handling
from threadit_core.api.identity import require_idempotency_key, require_user_id
from threadit_core.api.jwt_verify import configure_verifier
from threadit_core.config import load_settings
from threadit_core.logging import configure_logging
from threadit_core.repositories.dynamodb import (
    DynamoDBIdempotencyStore,
    DynamoDBRepository,
    build_table,
)
from threadit_core.repositories.keys import MaterializedPathBuilder
from threadit_core.repositories.s3_presigner import S3AttachmentPresigner, build_s3_client
from threadit_core.services.attachment_service import AttachmentService
from threadit_core.services.rate_limit import InMemoryRateLimiter
from threadit_core.services.write_service import WriteService


def build_write_service(settings) -> WriteService:
    table = build_table(
        table_name=settings.table_name,
        region=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
    )
    repo = DynamoDBRepository(table)
    idem = DynamoDBIdempotencyStore(table, ttl_seconds=settings.idempotency_ttl_seconds)
    return WriteService(
        posts=repo,
        comments=repo,
        comment_reader=repo,
        idempotency=idem,
        path_builder=MaterializedPathBuilder(max_depth=settings.max_comment_depth),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    configure_logging(settings.log_level)
    configure_verifier(settings.cognito_issuer or "", settings.cognito_audience)
    app.state.write_service = build_write_service(settings)
    app.state.rate_limiter = _build_rate_limiter(settings)
    app.state.rate_limit = settings.write_rate_limit
    app.state.rate_window = settings.write_rate_window_s
    if settings.attachments_bucket:
        s3 = build_s3_client(region=settings.aws_region, endpoint_url=settings.aws_endpoint_url)
        app.state.attachment_service = AttachmentService(
            presigner=S3AttachmentPresigner(s3, settings.attachments_bucket),
            max_bytes=settings.max_attachment_bytes,
        )
    else:
        app.state.attachment_service = None
    yield


def _build_rate_limiter(settings):
    if settings.redis_endpoint:
        import redis
        from threadit_core.repositories.redis_cache import RedisRateLimiter

        return RedisRateLimiter(redis.Redis(host=settings.redis_endpoint, port=6379))
    return InMemoryRateLimiter()


def enforce_rate_limit(request: Request, user_id: str = Depends(require_user_id)) -> str:
    limiter = request.app.state.rate_limiter
    decision = limiter.check(
        f"write:{user_id}",
        limit=request.app.state.rate_limit,
        window_seconds=request.app.state.rate_window,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail="rate limit exceeded",
            headers={"Retry-After": str(decision.retry_after)},
        )
    return user_id


def get_service(request) -> WriteService:
    return request.app.state.write_service


def get_attachment_service(request):
    svc = request.app.state.attachment_service
    if svc is None:
        from threadit_core.domain.errors import DomainError

        class _Unavailable(DomainError):
            status = 503
            error_type = "https://threadit/errors/attachments-unavailable"
            title = "Attachments not configured"

        raise _Unavailable("attachments bucket not configured")
    return svc


def create_app() -> FastAPI:
    app = FastAPI(title="Threadit post-write", version="1.0.0", lifespan=lifespan)
    install_cors(app, load_settings().cors_allow_origins)
    install_error_handling(app)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.post("/v1/attachments:presign")
    async def presign_draft(
        body: PresignRequest,
        request: Request,
        user_id: str = Depends(require_user_id),
    ) -> PresignResponse:
        svc = get_attachment_service(request)
        out = svc.presign_draft(
            user_id=user_id, content_type=body.contentType, size_bytes=body.sizeBytes
        )
        return PresignResponse(url=out.url, objectKey=out.object_key, expiresIn=out.expires_in)

    @app.post("/v1/posts", status_code=201)
    async def create_post(
        body: CreatePostRequest,
        request: Request,
        user_id: str = Depends(enforce_rate_limit),
        idem: str = Depends(require_idempotency_key),
    ) -> PostResponse:
        svc = get_service(request)
        post = svc.create_post(
            user_id=user_id,
            title=body.title,
            body=body.body,
            idempotency_key=idem,
            image_key=body.imageKey,
        )
        return PostResponse.of(post)

    @app.post("/v1/posts/{post_id}/comments", status_code=201)
    async def create_comment(
        post_id: str,
        body: CreateCommentRequest,
        request: Request,
        user_id: str = Depends(enforce_rate_limit),
        idem: str = Depends(require_idempotency_key),
    ) -> CommentResponse:
        svc = get_service(request)
        comment = svc.create_comment(
            user_id=user_id,
            post_id=post_id,
            text=body.text,
            parent_id=body.parentId,
            idempotency_key=idem,
        )
        return CommentResponse.of(comment)

    @app.post("/v1/posts/{post_id}/attachments:presign")
    async def presign_attachment(
        post_id: str,
        body: PresignRequest,
        request: Request,
        user_id: str = Depends(require_user_id),
    ) -> PresignResponse:
        svc = get_attachment_service(request)
        out = svc.presign(
            user_id=user_id,
            post_id=post_id,
            content_type=body.contentType,
            size_bytes=body.sizeBytes,
        )
        return PresignResponse(url=out.url, objectKey=out.object_key, expiresIn=out.expires_in)

    return app


app = create_app()
