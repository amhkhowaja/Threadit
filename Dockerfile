FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Runtime deps only (pinned).
RUN pip install --no-cache-dir \
    fastapi==0.115.5 pydantic==2.9.2 pydantic-settings==2.6.1 \
    boto3==1.35.54 structlog==24.4.0 "pyjwt[crypto]==2.9.0" \
    "uvicorn[standard]==0.32.0"

COPY libs/threadit_core/threadit_core /app/threadit_core
COPY services /app/services

# Non-root runtime user.
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser
USER 10001

# APP_MODULE selects the deployable: services.post_write.app or services.post_read.app
ENV APP_MODULE=services.post_write.app \
    PORT=8080

EXPOSE 8080
CMD ["sh", "-c", "uvicorn ${APP_MODULE}:app --host 0.0.0.0 --port ${PORT}"]
