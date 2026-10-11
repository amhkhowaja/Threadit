# Threadit — PLANNING

> Document 2 of 3 (ANALYSIS → **PLANNING** → SYSTEM_ARCHITECTURE).
> Status: Draft for review. Author: Senior System Architect.
> Basis: Executes the decisions **D1–D11** from `ANALYSIS.md`. Entity names (**Post, Comment, User**), the single table **`threadit`**, endpoints (`/v1/...`), **Idempotency-Key** on writes, and **Cognito + API Gateway** auth are carried forward verbatim and are formalized in `SYSTEM_ARCHITECTURE.md`.
> Golden rule: ***"billions" is a capacity ceiling, not a day-1 bill.*** Each phase adds cost/complexity only when it earns its keep.
> Phase gates: a phase is **Done** only when its **Exit Criteria** pass. **P3 Track B is blocked on D9.**

---

## 0. Phase overview

| Phase | Theme | Depends on | Key decisions enacted |
|-------|-------|-----------|-----------------------|
| **P1** | Infra + schema + API contracts + core read/write + auth on writes | — | D1, D2, D3, D6, D7, D10, D11 |
| **P2** | Images (S3 presigned) + caching (CloudFront/DAX/ElastiCache) + search (OpenSearch) | P1 Done | D4, D5, D8, D11 |
| **P3** | Subscriptions/feed + celebrity fan-out (**Track B, D9-gated**) + full observability/DR (Track A) | P2 Done | D9, D10 revisit |

Delivery model: trunk-based, PR-reviewed, Terraform-first (infra before app), environments **dev → staging → prod** with identical modules (parameterized capacity only, see §5).

---

## 1. PHASE 1 — Foundation (required first)

**Goal:** a correct, future-proof, horizontally-scalable foundation: Terraform infra, DynamoDB single-table schema (with timestamps), versioned API contracts, core write + read path, auth on writes, public reads, durable persistence (FR1–FR4, FR6). Streams enabled now (D1) with no consumer yet.

### 1.1 Development tasks

| ID | Task | Enacts | Dependencies | DoD |
|----|------|--------|--------------|-----|
| **P1-DEV-01** | Define access-pattern catalog (AP1–AP7) and finalize single-table key design | D2 | — | AP1–AP7 reviewed; keys/GSIs agreed (§1.6) |
| **P1-DEV-02** | Author **OpenAPI 3.1** `/v1` contract: `POST /posts`, `POST /posts/{id}/comments` (optional `parentId`), `GET /posts`, `GET /posts/{id}`, `GET /posts/{id}/comments` (tree-ordered + `depth`, optional `?rootCommentId=` for lazy subtree); cursor pagination; `Idempotency-Key`; RFC 9457 error model; `search_keyword` declared→501 | D3, D4, D7 | P1-DEV-01 | Spec validates; mock server passes contract tests |
| **P1-DEV-03** | **post-write service** (Fargate): validate, authz "write-as-self", idempotent conditional `PutItem` for Post/Comment; compute materialized `path`/`depth`/`rootCommentId` on reply; enforce **max depth 8** | D1, D3, D6, D11 | P1-DEV-02 | Unit + integration (DynamoDB Local/Testcontainers) green; idempotency replay test passes; depth-cap enforced |
| **P1-DEV-04** | **post-read service** (Fargate): `GET` post / comments / list (GSI1 latest, GSI2 by-user); **tree-ordered comment reads via `SK begins_with` + lazy subtree by `rootCommentId`**; cursor paging; `?consistent=true` for author | D1, D3, D7 | P1-DEV-02 | Reads return correct cursors + thread order; read-your-own-write test passes |
| **P1-DEV-05** | Auth integration: Cognito user pool, API GW JWT authorizer on write routes; mass-assignment + IDOR/BOLA guards | D6 | P1-DEV-03 | Negative authz tests in CI (write-as-other → 403; body-supplied userId ignored) |
| **P1-DEV-06** | Data-access layer (repository + DTOs) isolating DynamoDB (limits lock-in, R5) | D2 | P1-DEV-01 | No AWS types leak past repository boundary |
| **P1-DEV-07** | Contract + concurrency tests (idempotency, no read-modify-write on Post counters) | D1 | P1-DEV-03/04 | Concurrency suite green |

### 1.2 Deployment / Infrastructure tasks (Terraform)

| ID | Task | Notes | DoD |
|----|------|-------|-----|
| **P1-INFRA-01** | Terraform repo skeleton + remote state (S3 + DynamoDB lock) + modules layout | one module per concern; dev/staging/prod via tfvars | `terraform plan` clean in all envs |
| **P1-INFRA-02** | **VPC** (multi-AZ, private subnets, VPC endpoints for DynamoDB/S3 over NAT where possible) | D10; cost control (R4) | subnets/endpoints applied; no public app subnets |
| **P1-INFRA-03** | **DynamoDB table `threadit`**: PK/SK, GSI1/GSI2, **PITR**, **SSE-KMS**, **Streams=NEW_AND_OLD_IMAGES**, TTL on `IDEMPO#` | D1, D2 | table live; Streams ARN exported |
| **P1-INFRA-04** | **ECS Fargate** cluster + two services (read, write), autoscaling (CPU/RequestCount), least-priv task roles (write: Put/Update; read: Query/Get) | D1, D6, D11 | services healthy behind target groups |
| **P1-INFRA-05** | **API Gateway (HTTP API)** + request validation vs OpenAPI + Cognito JWT authorizer on writes + usage-plan scaffold | D6, D8 | routes resolve; writes require JWT; reads public |
| **P1-INFRA-06** | **WAF** rate-based rules on API GW | D8 | WAF attached; 429 on synthetic abuse |
| **P1-INFRA-07** | **Cognito** user pool + app client | D6 | sign-up/sign-in issues JWT |
| **P1-INFRA-08** | **CI/CD**: build → test → scan → plan → apply (dev auto, staging/prod gated); image scanning; no secrets in repo (KMS/Secrets Manager) | — | pipeline green dev→staging; prod manual gate |
| **P1-INFRA-09** | Baseline logs/metrics (structured JSON, correlationId, CloudWatch) — full observability deferred to P3 | — | request logs + basic dashboards |

### 1.6 DynamoDB single-table schema (authoritative — formalized in SYSTEM_ARCHITECTURE §4)

All items: `entityType`, `createdAt`, `updatedAt` (ISO-8601 UTC), `schemaVersion`.

| Item | PK | SK | GSI1PK / GSI1SK (latest) | GSI2PK / GSI2SK (by user) |
|------|----|----|--------------------------|----------------------------|
| **Post** | `POST#<postId>` | `META#<postId>` | `BUCKET#<yyyymmddhh>` / `TS#<createdAt>#<postId>` | `USER#<userId>` / `TS#<createdAt>#<postId>` |
| **Comment** | `POST#<postId>` | `COMMENT#<path>` (path = `<rootTs>#<ancestors…>#<ownTs>#<commentId>`) | — | `USER#<userId>` / `TS#<createdAt>#<commentId>` |
| **User** | `USER#<userId>` | `PROFILE#<userId>` | — | — |
| **Idempo** | `IDEMPO#<key>` | `IDEMPO#<key>` (TTL) | — | — |

**Threaded comments (D3):** `parentId` (null = top-level reply), `depth` (int), `rootCommentId` (top-level ancestor) are **active**. A `Query` `SK begins_with "COMMENT#"` returns the whole tree in thread order in one round trip; `SK begins_with "COMMENT#<rootPath>"` returns one subtree for lazy "load more replies." **Max depth cap = 8** ("continue thread" beyond). Reserved-for-future (non-breaking): `attachment` (images, D4/P2).**Latest-posts** uses hourly time-buckets to avoid a hot monotonic partition; **comment write-sharding** (`POST#<id>#<shard>`) is designed-for but off by default.

### 1.7 Phase 1 Exit Criteria
- FR1–FR4, FR6 demonstrable end-to-end in staging.
- Writes rejected without valid JWT; reads public; write-as-another-user blocked (403).
- Idempotent writes verified (replayed `Idempotency-Key` → no duplicate).
- Cursor pagination works for list + comments; author read-your-own-write passes.
- **Threaded replies work: nested `parentId` creates correct materialized paths; a single comment read returns the tree in thread order; depth cap (8) enforced; lazy subtree load by `rootCommentId` works.**
- `search_keyword` returns the defined **501** (not an error/scan).
- All infra reproducible via `terraform apply` in dev/staging; PITR + SSE-KMS + Streams on.

---

## 2. PHASE 2 — Images, Caching, Search

**Goal:** latency + capability layer. Enacts D4, D5, D8, D11. First **true CQRS read model** (OpenSearch) appears here.

### 2.1 Development tasks

| ID | Task | Enacts | Dependencies | DoD |
|----|------|--------|--------------|-----|
| **P2-DEV-01** | Image upload: `POST /v1/posts/{id}/attachments:presign` (presigned S3 PUT, type/size validation, per-user key prefix); write `attachment` ref | D11 | P1 | presign + direct PUT works; server never proxies bytes |
| **P2-DEV-02** | **Streams→Lambda indexer** → OpenSearch (idempotent upsert/delete, DLQ) | D4 | P1-INFRA-03 | docs indexed; poison → DLQ; lag < SLO |
| **P2-DEV-03** | Wire `GET /posts?search_keyword=` to OpenSearch (`search_after` cursor); 503-degrade search only when OpenSearch down | D4 | P2-DEV-02 | search returns ranked hits; non-search reads unaffected on OS outage |
| **P2-DEV-04** | Read-path caching: **DAX** for hot items/queries; single-flight + stale-while-revalidate (herd guard) | D5 | P1-DEV-04 | hit-ratio SLI emitted; herd test passes |
| **P2-DEV-05** | **ElastiCache** approximate comment counters + fine-grained rate-limit state | D5, D8 | — | counters eventually-correct; app rate limit returns 429+Retry-After |
| **P2-DEV-06** | **CloudFront** in front of reads/images (cache-control, OAC for private image bucket) | D5 | P2-DEV-01 | public GETs edge-cached; images served via OAC |

### 2.2 Deployment / Infrastructure tasks

| ID | Task | DoD |
|----|------|-----|
| **P2-INFRA-01** | **S3** private image bucket (SSE-KMS, lifecycle, block-public) + CloudFront OAC | upload/serve path works; bucket not public |
| **P2-INFRA-02** | **OpenSearch** domain (multi-AZ, encrypted) + Lambda event-source mapping on Streams + DLQ | indexer live; iterator-age alarm set |
| **P2-INFRA-03** | **DAX** cluster for read service | read service uses DAX; fallback to DynamoDB on DAX loss |
| **P2-INFRA-04** | **ElastiCache (Redis)** cluster | reachable from services; counters/rate-limit backed |
| **P2-INFRA-05** | **CloudFront + WAF** distribution for reads/images | edge cache + WAF live |
| **P2-INFRA-06** | **API Gateway usage plans/quotas** per endpoint class | read-class throttling independent of writes |
| **P2-INFRA-07** | **Cost dashboard** (per-service line-items), load tests to tune bucket granularity + write-shard threshold | tuned values recorded as decision-point outcomes |

### 2.3 Phase 2 Exit Criteria
- FR5 (image upload) end-to-end via presigned S3; images served via CloudFront OAC.
- Search returns relevant results with cursor paging; **p95 Streams→OpenSearch lag < 10 s**; search outage degrades search only (503), not other reads.
- Cache hit-ratio SLI live; herd/jitter verified under load; read-latency SLO met on hit path.
- Read-class rate limiting enforced (429 + Retry-After) without impacting writes.
- Load tests confirm GSI1 bucket granularity and comment write-shard threshold.

---

## 3. PHASE 3 — Subscriptions/Feed (Track B, D9-gated) + Observability/DR (Track A)

### Track A — Observability, SLOs, DR (unconditional)

| ID | Task | DoD |
|----|------|-----|
| **P3-INFRA-A1** | Distributed tracing (OpenTelemetry) + metrics (Prometheus/CloudWatch) + dashboards | traces across GW→service→DynamoDB; dashboards live |
| **P3-INFRA-A2** | SLO instrumentation + **error-budget burn-rate alerts** (§3.7) | alerts fire on synthetic burn |
| **P3-INFRA-A3** | **DR drill** (PITR restore rehearsal); revisit **multi-region (D10)** vs availability SLO | documented RTO/RPO; D10 decision recorded |
| **P3-INFRA-A4** | Runbooks (hot partition, OpenSearch lag, cache stampede, throttling) | runbooks reviewed |

### Track B — Subscriptions & Fan-out (**BLOCKED on D9**)

> If **D9 = shared board list**: Track B is **not built**; the board list (GSI1 latest) already satisfies the need; `user-subscriber` never enters the schema. Close Track B.
> If **D9 = personalized feed**: build the hybrid below on a Streams-fed **feed projection** (true CQRS read model #2).

| ID | Task | Enacts | DoD |
|----|------|--------|-----|
| **P3-DEV-B1** | Subscription endpoints (`POST/DELETE /v1/users/{id}/subscription`) + subscriber graph item type | D9 | subscribe/unsubscribe works |
| **P3-DEV-B2** | **Feed projection store** + Streams fan-out workers (Lambda) | D9, D11 | projection built from Streams |
| **P3-DEV-B3** | **Hybrid fan-out**: push (fan-out-on-write) for normal authors; **pull (fan-out-on-read) for celebrities**; merge at read | D9 | celebrity write stays cheap; feed read bounded |
| **P3-DEV-B4** | `GET /v1/feed` (cursor) with documented lag | D9, D7 | feed returns merged, paged results |

### 3.7 SLOs / SLIs (formalized in SYSTEM_ARCHITECTURE §7)
Recommended starting targets (confirm with product): read-hit p99 ≤ 50 ms; overall read p99 ≤ 150 ms; write p99 ≤ 300 ms; availability ≥ 99.95% (single-region multi-AZ); search freshness p95 < 10 s; read-your-own-write 100% via narrow ConsistentRead. Raising availability to 99.99% forces the multi-region (D10) decision — cost impact flagged.

### 3.8 Phase 3 Exit Criteria
- Track A: tracing/metrics/dashboards live; burn-rate alerts tested; DR drill passed; D10 revisited and recorded.
- Track B (only if D9=feed): hybrid fan-out verified — celebrity author write latency bounded, celebrity-follower feed read bounded; feed lag documented.

---

## 4. Cross-phase dependencies (summary)
- P1-INFRA-03 (Streams on) → unblocks P2-DEV-02 (indexer) and P3-DEV-B2 (fan-out) with **no table change**.
- P1-DEV-02 (OpenAPI, search declared→501) → P2-DEV-03 wires search **without a contract change**.
- P1 schema reserves `attachment`/`parentId` → P2 images and future threading are **additive**.
- **D9 gates all of Track B**; must be resolved before P3 starts.

---

## 5. Environment & dev/prod parity (formalized in SYSTEM_ARCHITECTURE §10)
- **Same Terraform modules** across dev/staging/prod; only **capacity parameters** differ.
- **Dev:** DynamoDB on-demand, single small Fargate task, **no DAX/OpenSearch/ElastiCache until P2**, traces 100%.
- **Prod:** provisioned + autoscaling, multi-AZ, right-sized caches/cluster, sampled traces.
- **Must NEVER differ:** auth path (Cognito + authorizer), idempotency, single-table schema, `/v1` contract, WAF presence, PITR + SSE-KMS encryption, least-privilege IAM.

---

## 6. Open decision gates carried into execution
- **D9** (feed vs board list) — gates P3 Track B. **Resolve before P3.**
- Exact SLO numbers (§3.7) — confirm with product; 99.99% forces D10 multi-region.
- GSI1 bucket granularity + GSI projection attributes — tune in P2-INFRA-07.
- Comment write-shard activation threshold — tune in P2-INFRA-07.
- D3 threaded replies (materialized path, depth 8) — **decided**; confirm depth cap / read shape if you want different defaults.
