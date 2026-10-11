# Threadit — DEVELOPMENT STRATEGY

> Companion to `ANALYSIS.md`, `PLANNING.md`, `SYSTEM_ARCHITECTURE.md`, `FLOCI_AWS_SERVICES_COMPATIBILITY.md`.
> Status: Draft for review. Author: Senior System Architect (crew: API / Database / Security).
> Fixes the *how* of building Phase 1 (and the seams for P2/P3) in **Python 3.12 + FastAPI, OOP, TDD**.
>
> **Three governing principles from the product owner (binding):**
> 1. **AWS-managed-service-first** — push work into managed services (API Gateway Cognito authorizer, WAF, DynamoDB conditional writes / TTL / Streams, Cognito). The app does the least it can.
> 2. **Infrastructure before code** — Terraform is authored and stood up (on Floci first) before services are written.
> 3. **Minimal code volume** — the Python services are thin `HTTP → validate → repository → DynamoDB` layers. Every line must earn its place.
>
> **Rule:** no new architectural decision is taken unilaterally during development. Anything the docs leave open is surfaced to the product owner as a flagged decision point. Approved implementation decisions are recorded in §2 (I1–I10).

---

## 1. Approach

- **Language/stack:** Python 3.12, FastAPI, Pydantic v2, boto3, structlog, PyJWT. Package/dependency manager: **uv** (lockfile with hashes).
- **Style:** object-oriented, layered, dependency-injected, abstractions at every boundary. Minimal comments (names carry intent).
- **TDD:** red → green → refactor. Tests are written before implementation for every task. No task is "done" until its tests pass and its PLANNING DoD is met.
- **Managed-first:** auth verification (API GW Cognito authorizer), rate limiting (WAF), idempotency/TTL/streams (DynamoDB) are configured in Terraform, not re-implemented in Python.
- **Dev/prod parity:** one Terraform codebase; dev targets Floci (`localhost:4566`), prod targets real AWS. One app-level config difference: `aws_endpoint_url`.

---

## 2. Approved implementation decisions (I1–I10)

Recorded so the test suite and code encode the agreed values. Adjusted for *managed-first / minimal-code*.

| ID | Decision | Chosen | Rationale |
|----|----------|--------|-----------|
| I1 | Topology | One monorepo + shared `threadit_core` lib + **two thin apps** (`post_write`, `post_read`), separate IAM task roles | Managed IAM does privilege separation (write=Put/Update, read=Query/Get); keeps each app tiny (ADR-002/§10) |
| I2 | JWT library | `pyjwt[crypto]` | Maintained, fewer CVEs; only used if/where app inspects claims |
| I3 | In-service JWT re-verification | **Dropped in P1** | API GW Cognito authorizer (managed) verifies; service trusts gateway-injected claims, reads `sub`. Less code |
| I4 | Logging | `structlog` JSON + central **redaction** processor + correlationId contextvar | One processor chain redacts everywhere; satisfies R13 |
| I5 | Dependency injection | FastAPI `Depends` + tiny hand-rolled container (built in lifespan, on `app.state`) | No extra DI framework; `dependency_overrides` for tests |
| I6 | Sizes (contract) | title 1..300, body ≤ 40 000, text ≤ 10 000, HTTP body ≤ 256 KB, limit 1..100 default 20 | Keeps items well under DynamoDB 400 KB; `extra="forbid"` on inbound |
| I7 | Cursor | Plain opaque base64url of `LastEvaluatedKey`, defensively validated (strict decode + key-shape) | No HMAC subsystem in P1 → less code; forged-cursor pivot still blocked |
| I8 | Idempotency TTL | 24 h; `IDEMPO#<key>` conditional `PutItem(attribute_not_exists)` | Managed DynamoDB TTL does expiry |
| I9 | `commentCountApprox` | **Deferred to P2** | No read-modify-write counter race in P1 (R2) |
| I10 | Package manager | **uv** | Fast, reproducible lockfile with hashes (A06) |

Floci-specific implementation decisions (from `FLOCI_AWS_SERVICES_COMPATIBILITY.md`) carried in: pin the Floci image (F8); IAM denies (F1) and WAF throttling (F2) are **staging-verified**, not asserted against Floci.

---

## 3. Build sequence (infrastructure before code)

```
P1 order of work:
  A. IaC skeleton + remote state (Floci)        [P1-INFRA-01]
  B. DynamoDB table `threadit` module           [P1-INFRA-03]   ← data core first
  C. Cognito + API Gateway (authorizer) + WAF    [P1-INFRA-05/06/07]
  D. ECS Fargate services + least-priv roles     [P1-INFRA-04]  (image comes from H)
  E. VPC + endpoints                             [P1-INFRA-02]
  —— infra stands up on Floci; `terraform apply` green ——
  F. Access-pattern catalog + OpenAPI /v1        [P1-DEV-01/02]  (tests first)
  G. threadit_core: domain + DTOs + repo ABCs + mapper + cursor + logging  [P1-DEV-06]
  H. post_write + post_read thin apps            [P1-DEV-03/04/05]
  I. contract + concurrency + security tests     [P1-DEV-07]
  J. Makefile targets + Dockerfile + CI          [P1-INFRA-08/09]
  K. end-to-end verify on Floci; staging gate    [P1 exit §1.7]
```

Infra (A–E) is authored first so the data core and managed auth exist before the thin services bind to them.

---

## 4. IaC strategy (dev=Floci / prod=AWS)

Per `FLOCI_AWS_SERVICES_COMPATIBILITY.md §4`:
- One module per concern under `terraform/modules/` (`dynamodb`, `cognito`, `apigw`, `waf`, `ecs`, `network`, `iam`).
- `terraform/envs/dev.tfvars` → `use_floci=true`, on-demand/single-node, `enable_dax=false`, `enable_xray=false`.
- `terraform/envs/prod.tfvars` → `use_floci=false`, provisioned+autoscaling, multi-AZ.
- Single `aws` provider with a `use_floci` toggle driving `endpoints {}` + `skip_*` + `s3_use_path_style` (exact block in FLOCI doc §4.1).
- Remote state: Floci S3+DynamoDB-lock in dev; real S3+DynamoDB-lock in prod.
- **Must-never-differ** (PLANNING §5): auth path, idempotency, single-table schema, `/v1` contract, WAF presence, PITR + SSE-KMS, least-priv IAM.
- **Managed-first expression in IaC:** DynamoDB `stream_enabled` + TTL + PITR + SSE-KMS; API GW JWT authorizer referencing the Cognito pool; WAF rate-based rule — all declared in Terraform so the app needs no equivalent code.

---

## 5. Service development (OOP, DI, minimal)

Layering (both apps, shared via `threadit_core`):

```
router (FastAPI)  ── thin: parse DTO, call use-case, map result/error
   │ Depends
application service (use-case)  ── orchestration, authz-as-self, idempotency
   │ interface
repository (ABC port)  ── domain-typed; DynamoDB adapter is the only boto3 site
   │
domain (pure dataclasses) + Pydantic v2 DTOs at the edge
```

- **DI (I5):** singletons (boto3 resource, repositories, config) built once in the FastAPI `lifespan` and attached to `app.state`; request-scoped wiring via `Depends`; tests swap implementations with `app.dependency_overrides`.
- **No AWS type crosses the repository boundary** (enforced by `import-linter` in CI) — protects against lock-in (R5) and keeps use-cases pure/unit-testable without AWS.
- **Mass-assignment guard (R9):** inbound DTOs carry only user-authored fields (`extra="forbid"`); `userId` comes from the gateway-verified `sub`; server computes `id`, timestamps, `path`, `depth`, `rootCommentId`.
- **Thinness check:** each router handler is a few lines; business rules live in the use-case; persistence detail lives in the adapter. If a handler grows logic, it moves down a layer.

Shared `threadit_core` owns: domain models, DTOs, `KeyFactory`/`ItemMapper`, `CursorCodec`, RFC 9457 error mapping, `MaterializedPathBuilder` (+ depth-cap-8 → `MaxDepthExceeded`→422), structlog config + redaction, config (`pydantic-settings`).

---

## 6. Logging strategy (levels + redaction, R13)

- **structlog**, JSON renderer, one processor chain shared by both apps.
- **Levels:** `DEBUG` (dev inner loop; never full request bodies in prod), `INFO` (request start/finish, security events: authn fail, 403, 409 idempotency conflict, 422 depth cap), `ERROR` (handled failures with stable error code + correlationId, no stack traces to client).
- **Redaction processor (mandatory, runs before the JSON renderer):** masks denylisted keys (`authorization`, `token`, `access_token`, `refresh_token`, `id_token`, `jwt`, `bearer`, `password`, `secret`, `apikey`, `cookie`, `set-cookie`, `idempotency-key`) and regex-masks bearer/JWT patterns in free text. **Never log** tokens, Authorization headers, secrets, or PII.
- **correlationId:** read inbound `X-Correlation-Id` / API-GW request id or generate UUIDv4; bound to a contextvar so every line inherits it; echoed in the RFC 9457 response envelope.
- **Log level is config-driven** per environment.

---

## 7. Security / OWASP (from the security review)

Phase-1 gates (MUST), full checklist tracked in the security review output:
- Writes require Cognito JWT (managed authorizer); reads public; fail-closed. (A01/A07, API2/API5)
- `userId` only from verified `sub`; ignore client id/userId/timestamps; `extra="forbid"`; outbound allow-list DTOs. (API1/API3/API6, R9)
- Parameterized DynamoDB expressions only; validate sizes (I6); defensive cursor decode; depth-cap→422; `search_keyword`→501 (no scan). (A03/API4/API8)
- Secrets only via env/SSM/Secrets Manager; `.env` holds Floci dummy creds only; `.gitignore` covers `.env`/`*.tfvars`/state. (A05, R13)
- Structured logs with redaction (§6). (A09)
- Deps pinned with hashed lockfile; CI runs `pip-audit` (CVE), `gitleaks`/`trufflehog` (secrets incl. git history), `semgrep` (SAST), CycloneDX SBOM. **These scanners are missing locally → installed in CI; a grep fallback is not an acceptable gate.** (A06/A08)
- **Staging-verified (not provable on Floci):** IAM least-privilege denies (F1), WAF throttling (F2), TLS, PITR/DR.

---

## 8. Testing strategy (TDD)

| Layer | What | Tooling | Runs on |
|-------|------|---------|---------|
| **Unit** | domain, use-cases, path builder, cursor codec, mapper, redaction, validation — no AWS | `pytest` + fakes (in-memory repo) | local, fast, every commit |
| **Integration** | repository adapter against real DynamoDB API; idempotency replay; tree/subtree queries; GSI1/GSI2; read-your-own-write | `pytest` + **Floci** (`testcontainers-floci` or compose) | local + CI |
| **Contract** | generated `openapi.json` diffed against `openapi/v1.yaml`; request/response schema conformance; error envelope | `pytest` + `schemathesis` | CI (P1-DEV-02 gate) |
| **Security** | write-as-other→403; body-supplied userId ignored (assert persisted item); forged cursor→400; missing/!UUID Idempotency-Key→400; depth-9→422; search_keyword→501 | `pytest` | CI |
| **Concurrency** | parallel identical idempotent writes → single item; no read-modify-write on counters | `pytest` + threads/async | CI |
| **Load** | read p99 / write p99 against **staging on real AWS**; WAF throttle; cache (P2) | `k6`/`locust` | staging only (not Floci — F2) |
| **Deployment** | `terraform apply` + smoke (create post → read it → threaded reply → list) on **both** Floci (dev) and real AWS (staging) | `make` targets + smoke script | dev=Floci, staging=AWS |

Coverage gate and the full suite run in CI; deployment tests run against both targets per the explicit requirement.

---

## 9. Build & deployment (Makefile)

`make` is the single entry point (details realized in P1-INFRA-08). Target set:

```
make install        # uv sync (locked, hashed)
make lint           # ruff + import-linter (no AWS type past repo boundary)
make test           # unit + contract + security (no AWS)
make itest          # integration against Floci
make floci-up       # docker compose up Floci (pinned image, persistent mode)
make floci-down
make tf-plan ENV=dev|prod
make tf-apply ENV=dev|prod      # dev=Floci endpoints, prod=real AWS (prod gated/confirm)
make build          # docker build both service images (non-root, minimal base)
make deploy ENV=dev|prod        # push image + terraform apply ECS service
make scan           # pip-audit + gitleaks + semgrep + SBOM (CI)
make smoke ENV=dev|prod         # end-to-end deployment test
make e2e            # floci-up + tf-apply dev + smoke dev
```

- **Dockerfile:** slim Python base, non-root user, no secrets in layers, two images (or one image + entrypoint selecting the app) — chosen for minimal volume.
- **CI/CD (P1-INFRA-08):** build → test → scan → `tf-plan` → `tf-apply` (dev auto; staging/prod gated). Prod apply always requires explicit human confirmation (high-risk).

---

## 10. Phase decomposition (tasks map to PLANNING IDs)

**Phase 1 (now):** infra A–E then code F–K (see §3). Tasks: `P1-INFRA-01..09`, `P1-DEV-01..07`. Exit = PLANNING §1.7.
**Phase 2:** images (S3 presigned), caching (DAX/ElastiCache/CloudFront), search (OpenSearch via Streams→Lambda). Tasks: `P2-DEV-01..06`, `P2-INFRA-01..07`. Seams kept open in P1 (`attachment` reserved; Streams on; rate-limit abstraction no-op; search→501).
**Phase 3:** observability/DR (Track A, unconditional) + subscriptions/feed/fan-out (Track B, **gated on D9**). Tasks: `P3-INFRA-A1..A4`, `P3-DEV-B1..B4`.

---

## 11. Open items carried into development (not decided unilaterally)
- **D9** feed vs board list — gates P3 Track B.
- Exact SLO numbers; GSI1 bucket granularity; comment write-shard threshold — tuned in P2 load tests.
- `[VERIFY]` Floci operation-level items (PITR, API-GW usage-plan enforcement, Cognito claim shape) — confirm in staging before P1 exit.
- Any new decision that surfaces mid-build is raised to the product owner, not taken here.
