from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, Request
from threadit_core.api.dtos import CommentResponse, PageResponse, PostResponse
from threadit_core.api.errors import install_error_handling
from threadit_core.config import load_settings
from threadit_core.logging import configure_logging
from threadit_core.repositories.dynamodb import DynamoDBRepository, build_table
from threadit_core.repositories.opensearch import OpenSearchIndex
from threadit_core.repositories.search_index import SearchHit
from threadit_core.services.read_service import ReadService


def build_read_service(settings) -> ReadService:
    table = build_table(
        table_name=settings.table_name,
        region=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
    )
    repo = DynamoDBRepository(table)
    search = OpenSearchIndex(settings.opensearch_endpoint) if settings.opensearch_endpoint else None
    return ReadService(
        posts=repo,
        comments=repo,
        default_limit=settings.default_page_limit,
        max_limit=settings.max_page_limit,
        search=search,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    configure_logging(settings.log_level)
    app.state.read_service = build_read_service(settings)
    yield


def get_service(request: Request) -> ReadService:
    return request.app.state.read_service


def create_app() -> FastAPI:
    app = FastAPI(title="Threadit post-read", version="1.0.0", lifespan=lifespan)
    install_error_handling(app)

    @app.get("/healthz")
    async def healthz() -> dict:
        return {"status": "ok"}

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
        page = svc.list_posts(
            user_id=user_id, search_keyword=search_keyword, limit=limit or last, cursor=cursor
        )
        items = [
            PostResponse.of_hit(p) if isinstance(p, SearchHit) else PostResponse.of(p)
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
        return PostResponse.of(svc.get_post(post_id, consistent=consistent))

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
