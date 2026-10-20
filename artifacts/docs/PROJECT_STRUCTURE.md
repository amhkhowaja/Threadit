# Threadit — Project Structure

> A map of the repository: what each top-level directory holds, how the layers
> relate, and where to make common changes. Reflects the repo as built
> (Phases 1 & 2, plus the launch/seed tooling and docs).

## Guiding principles

- **Framework-agnostic core.** All domain logic, data mapping, and use-cases live in a
  plain-Python library (`libs/threadit_core`) with no web framework imports. The
  deployables (`services/`) are thin adapters over that core. An import-linter contract
  forbids `boto3`/`botocore` from crossing into `domain`/`services`/`repositories.ports`.
- **One codebase, two targets.** The same Terraform runs against the Floci emulator (dev)
  and real AWS (prod) via a `use_floci` provider toggle and `enable_*` capability flags.
- **Infrastructure before code.** Terraform modules are authored per concern and stood up
  (on Floci first) before the services that depend on them.

## Top-level layout

```
Threadit/
├── libs/threadit_core/     # framework-agnostic core library (domain + use-cases + adapters)
├── services/               # deployable adapters (FastAPI apps + Lambda handlers)
├── frontend/               # React + TS + Vite + Tailwind SPA
├── terraform/              # IaC: modules per concern + per-env tfvars
├── tests/                  # unit / api / contract / integration / load
├── tools/                  # dev utilities (OpenAPI gen, smoke, real-AWS e2e)
├── scripts/                # app launch + demo seeding shell/python scripts
├── docs/                   # rendered assets for the README (architecture, nfr, screenshots)
├── artifacts/docs/         # design & process docs (planning, analysis, this file)
├── openapi/                # generated OpenAPI v1 contract
├── build/                  # assembled Lambda packages (generated; gitignored)
├── Dockerfile              # single image; APP_MODULE selects read vs write service
├── compose.yaml            # Floci emulator for local dev
├── Makefile                # developer entrypoints (setup, app-*, seed, check, tf-*)
├── pyproject.toml          # deps, ruff, pytest, import-linter config
└── README.md               # quickstart, AWS path, system design, NFR
```

## `libs/threadit_core/threadit_core/` — the core library

The heart of the system; imported by every service. No FastAPI, no AWS SDK above the
repository boundary.

```
threadit_core/
├── config.py               # pydantic-settings: all THREADIT_* env config (one source)
├── logging.py              # structlog setup + secret/PII redaction
├── domain/                 # pure domain layer (no I/O)
│   ├── models.py           # Post, Comment, Page (dataclasses/value objects)
│   ├── errors.py           # DomainError hierarchy -> HTTP status mapping
│   └── author.py           # stable author handle derived from userId
├── services/               # use-cases (orchestration; depend on repository *ports*)
│   ├── write_service.py    # create post/comment: idempotency, materialized-path threading
│   ├── read_service.py     # get/list posts + comments; wraps reads in the single-flight cache
│   ├── stream_indexer.py   # DynamoDB Stream record -> OpenSearch projection (CQRS)
│   ├── attachment_service.py # presign validation (type allow-list, size cap)
│   ├── image_url.py        # resolve image URL (CloudFront prod / presigned GET local)
│   ├── cache.py            # SingleFlightCache: request coalescing + stale-while-revalidate
│   └── rate_limit.py       # RateLimiter/Counter ports + InMemory impls + decisions
├── repositories/           # adapters (the ONLY place boto3 is allowed)
│   ├── ports.py            # abstract repository interfaces the services depend on
│   ├── dynamodb.py         # DynamoDBRepository + idempotency store + build_table/build_dax_table
│   ├── keys.py             # single-table key factory + materialized-path builder
│   ├── mapper.py           # domain <-> DynamoDB item mapping
│   ├── cursor.py           # opaque pagination cursor codec
│   ├── opensearch.py       # OpenSearch adapter (SigV4-signed in prod)
│   ├── search_index.py     # SearchIndex port + SearchHit/SearchPage
│   ├── s3_presigner.py     # S3 presigned PUT/GET
│   ├── presigner.py        # AttachmentPresigner port
│   └── redis_cache.py      # RedisRateLimiter + RedisCounter (ElastiCache)
└── api/                    # HTTP concerns reused by both apps
    ├── dtos.py             # request/response models (the wire contract)
    ├── identity.py         # require_user_id (Cognito JWT -> sub; x-user-id dev fallback)
    ├── jwt_verify.py       # in-service Cognito access-token verification (JWKS)
    ├── errors.py           # RFC 9457 problem+json error handling + correlation
    └── cors.py             # CORS install helper
```

Layering: `api` and `services` depend on `domain` and `repositories.ports`; only
`repositories/*` concrete adapters touch AWS SDKs.

## `services/` — the deployables

One container image (`Dockerfile`); `APP_MODULE` selects which app runs.

```
services/
├── post_read/app.py        # FastAPI read API  (:8080, public GET) — builds ReadService + cache
├── post_write/app.py       # FastAPI write API (:8081, auth POST) — rate limit + attachments
├── indexer/handler.py      # Lambda: DynamoDB Streams -> StreamIndexer -> OpenSearch (+ SQS DLQ)
└── loadgen/handler.py      # Lambda: in-VPC DynamoDB latency probe (perf testing only)
```

The ALB path-routes write methods (POST/PUT/DELETE/PATCH) to `post_write`, everything
else to `post_read`.

## `frontend/` — the SPA

```
frontend/
├── src/
│   ├── config.ts           # runtime config from env (the single plug-in point)
│   ├── brand.ts            # design tokens (rebrand here)
│   ├── theme.ts            # tokens -> CSS variables
│   ├── lib/
│   │   ├── api/            # typed /v1 client + DTOs
│   │   ├── auth/           # Cognito OIDC (PKCE), in-memory token, AuthProvider
│   │   └── hooks.ts        # TanStack Query hooks
│   ├── components/         # PostList, CommentTree, Composer, Layout bits
│   └── pages/              # Home, PostDetail, Create, Search, Auth, AuthCallback
├── e2e/                    # Playwright specs
├── .env.aws.example        # backend target presets (copy to .env.local)
└── .env.local-floci.example
```

Backend target is chosen by copying an env preset to `.env.local`; no component code
changes to switch between Floci/local and real AWS.

## `terraform/` — infrastructure as code

```
terraform/
├── main.tf                 # wires all modules; provider toggles for Floci vs AWS
├── variables.tf            # enable_* capability flags + inputs
├── outputs.tf              # resource identifiers (ALB DNS, Cognito IDs, etc.)
├── envs/                   # per-target tfvars
│   ├── dev.tfvars          # Floci (local emulator)
│   ├── prod.tfvars         # control-plane prod
│   ├── prodweb.tfvars      # full prod web incl. frontend CloudFront
│   ├── awsbackend.tfvars   # prod backend, no CloudFront (frontend runs locally)
│   └── awsverify.tfvars    # full non-CloudFront verify profile
└── modules/                # one module per concern
    ├── dynamodb/  network/  iam/  cognito/        # always-on core
    ├── ecr/  ecs_alb/  frontend/                  # prod web (ALB + Fargate + SPA host)
    ├── opensearch/  indexer/                      # search + Streams consumer
    ├── s3_images/  cloudfront/                    # images + CDN
    ├── dax/  elasticache/                         # cache tier
    ├── apigw/  ecs/  waf/                          # legacy/edge (superseded or edge-gated)
    └── loadgen/                                   # perf-probe Lambda
```

Capability flags in `variables.tf` (`enable_prod_web`, `enable_search`, `enable_dax`,
`enable_elasticache`, `enable_frontend_cdn`, `enable_images_cdn`, `enable_apigw`, …)
select which modules instantiate for a given env.

## `tests/`

```
tests/
├── unit/                   # pure logic (no AWS): mapper, cache, rate limit, read/write svc, DAX/Redis wiring
├── api/                    # FastAPI TestClient with injected fakes (no AWS)
├── contract/               # OpenAPI contract check
├── integration/            # against Floci/real backends (opensearch, dynamodb, s3, dax, redis)
├── load/                   # multi-user NFR/async harness (run_nfr.py, harness.py)
└── fakes.py                # in-memory repository fakes shared by unit/api tests
```

`make check` runs lint + import-linter + unit/api/contract (no AWS). Integration tests
are marked `integration` and skip unless their backend endpoint env is set.

## `tools/` and `scripts/`

```
tools/
├── gen_openapi.py          # regenerate openapi/v1.json from the apps
├── smoke.py                # in-process end-to-end smoke (Floci)
└── e2e_realaws.py          # full-app e2e against real AWS

scripts/
├── setup.sh                # one-command contributor setup
├── run-floci.sh            # full local stack on Floci  (make app-floci)
├── run-aws.sh              # local frontend -> deployed AWS backend  (make app-aws)
├── aws-deploy.sh           # build+push image, apply/destroy AWS backend (make aws-up/down)
├── stop.sh                 # stop local processes  (make app-stop)
└── seed/                   # demo seeding: scrape.py (HN+Lemmy) -> seed.py (clean-slate) ; make seed
```

## `docs/` vs `artifacts/docs/`

- **`docs/`** holds rendered assets referenced by the README: `architecture/` (the
  implemented-architecture SVG + its generator + AWS icons), `nfr/` (load-test graphs +
  generator), and `screenshots/`.
- **`artifacts/docs/`** holds the design and process record: `PLANNING.md`,
  `ANALYSIS.md`, `SYSTEM_ARCHITECTURE.md`, `DEVELOPMENT_STRATEGY.md`,
  `FLOCI_AWS_SERVICES_COMPATIBILITY.md`, `NFR_REPORT.md`, the phase completion summaries,
  the frontend prompt, and this document.

## Where to make common changes

| I want to… | Edit |
|---|---|
| Change an API request/response shape | `libs/threadit_core/api/dtos.py` (then `make openapi`) |
| Add/adjust a use-case rule | `libs/threadit_core/services/*` |
| Change how data is stored/queried | `repositories/dynamodb.py`, `keys.py`, `mapper.py` |
| Add an env setting | `config.py` (+ pass it through in the service `app.py` / Terraform env) |
| Add/flip an AWS capability | `terraform/variables.tf` + the relevant `envs/*.tfvars` |
| Rebrand or re-point the frontend | `frontend/src/brand.ts` / `frontend/.env.local` |
| Run the app locally / seed it | `make app-floci`, `make seed` |
