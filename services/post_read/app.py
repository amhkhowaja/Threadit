from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from threadit_core.api.cors import install_cors
from threadit_core.api.dtos import CommentResponse, PageResponse, PostResponse
from threadit_core.api.errors import install_error_handling
from threadit_core.api.identity import require_user_id
from threadit_core.api.jwt_verify import configure_verifier
from threadit_core.config import load_settings
from threadit_core.domain.author import author_handle
from threadit_core.logging import configure_logging
from threadit_core.repositories.dynamodb import DynamoDBRepository, build_dax_table, build_table
from threadit_core.repositories.opensearch import OpenSearchIndex
from threadit_core.repositories.s3_presigner import S3AttachmentPresigner, build_s3_client
from threadit_core.repositories.search_index import SearchHit
from threadit_core.services.image_url import ImageUrlResolver
from threadit_core.services.read_service import ReadService


def build_read_service(settings) -> ReadService:
    if settings.dax_endpoint:
        # Cached reads via DAX; ConsistentRead requests (read-your-own-write) are
        # passed through to DynamoDB by DAX, so correctness is preserved.
        table = build_dax_table(
            table_name=settings.table_name,
            region=settings.aws_region,
            dax_endpoint=settings.dax_endpoint,
        )
    else:
        table = build_table(
            table_name=settings.table_name,
            region=settings.aws_region,
            endpoint_url=settings.aws_endpoint_url,
        )
    repo = DynamoDBRepository(table)
    search = (
        OpenSearchIndex(
            settings.opensearch_endpoint,
            sign=settings.opensearch_sign,
            region=settings.aws_region,
        )
        if settings.opensearch_endpoint
        else None
    )
    return ReadService(
        posts=repo,
        comments=repo,
        default_limit=settings.default_page_limit,
        max_limit=settings.max_page_limit,
        search=search,
        post_cache=_build_post_cache(settings),
    )


def _build_post_cache(settings):
    if settings.read_cache_ttl_s <= 0:
        return None
    from threadit_core.services.cache import SingleFlightCache

    return SingleFlightCache(
        ttl=settings.read_cache_ttl_s,
        stale_ttl=settings.read_cache_stale_ttl_s,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    configure_logging(settings.log_level)
    configure_verifier(settings.cognito_issuer or "", settings.cognito_audience)
    app.state.read_service = build_read_service(settings)
    app.state.image_resolver = _build_image_resolver(settings)
    yield


def _build_image_resolver(settings) -> ImageUrlResolver:
    presigner = None
    if settings.attachments_bucket and not settings.images_cloudfront_domain:
        s3 = build_s3_client(region=settings.aws_region, endpoint_url=settings.aws_endpoint_url)
        presigner = S3AttachmentPresigner(s3, settings.attachments_bucket)
    return ImageUrlResolver(
        cloudfront_domain=settings.images_cloudfront_domain,
        presigner=presigner,
    )


def get_service(request: Request) -> ReadService:
    return request.app.state.read_service


def get_image_resolver(request: Request) -> ImageUrlResolver:
    return request.app.state.image_resolver


def create_app() -> FastAPI:
    app = FastAPI(title="Threadit post-read", version="1.0.0", lifespan=lifespan)
    install_cors(app, load_settings().cors_allow_origins)
    install_error_handling(app)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/v1/me")
    async def me(request: Request) -> dict:
        user_id = require_user_id(request)
        return {"userId": user_id, "authorName": author_handle(user_id)}

    @app.get("/v1/posts")
    async def list_posts(
        request: Request,
        limit: int | None = Query(default=None),
        cursor: str | None = Query(default=None),
        user_id: str | None = Query(default=None),
        search_keyword: str | None = Query(default=None),
        last: int | None = Query(default=None),
    ) -> PageResponse:
        svc = get_service(request)
        resolver = get_image_resolver(request)
        page = svc.list_posts(
            user_id=user_id, search_keyword=search_keyword, limit=limit or last, cursor=cursor
        )
        items = [
            PostResponse.of_hit(p)
            if isinstance(p, SearchHit)
            else PostResponse.of(p, resolver.url_for(p.image_key))
            for p in page.items
        ]
        return PageResponse(
            items=items,
            nextCursor=page.next_cursor,
            limit=limit or last or svc.default_limit,
        )

    @app.get("/v1/posts/{post_id}")
    async def get_post(
        post_id: str,
        request: Request,
        consistent: bool = Query(default=False),
    ) -> PostResponse:
        svc = get_service(request)
        resolver = get_image_resolver(request)
        post = svc.get_post(post_id, consistent=consistent)
        return PostResponse.of(post, resolver.url_for(post.image_key))

    @app.get("/v1/posts/{post_id}/comments")
    async def list_comments(
        post_id: str,
        request: Request,
        limit: int | None = Query(default=None),
        cursor: str | None = Query(default=None),
        rootCommentId: str | None = Query(default=None),
    ) -> PageResponse:
        svc = get_service(request)
        page = svc.list_comments(post_id, root_comment_id=rootCommentId, limit=limit, cursor=cursor)
        return PageResponse(
            items=[CommentResponse.of(c) for c in page.items],
            nextCursor=page.next_cursor,
            limit=limit or svc.default_limit,
        )

    return app


app = create_app()
