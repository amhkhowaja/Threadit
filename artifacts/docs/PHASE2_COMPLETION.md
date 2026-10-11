# Threadit — Phase 2 Completion Summary

> Status: **Phase 2 complete.** Verified on Floci (dev) and real AWS (us-east-1 then eu-central-1).
> Delivers: image upload, search (first true CQRS read model), caching + rate limiting, and a real NFR/load pass.

## What Phase 2 adds (on top of P1)

### Images (P2-DEV-01 / P2-INFRA-01)
- `POST /v1/posts/{id}/attachments:presign` → presigned S3 PUT; type allow-list (415), size cap (413), per-user key; server never proxies bytes.
- S3 module: private/block-public, SSE-KMS, versioning, CloudFront OAC (gated); write role least-priv `s3:PutObject`.
- Verified: real presigned PUT uploads bytes to Floci S3 (integration test).

### Search — first true CQRS read model (P2-DEV-02/03 / P2-INFRA-02)
- `StreamIndexer` projects DynamoDB Stream Post records → OpenSearch (idempotent, non-Post ignored, replay-safe).
- Lambda indexer on DynamoDB Streams ESM (batch 100) + SQS DLQ on failure.
- `OpenSearchIndex` adapter: **SigV4-signed on AWS**, unsigned on Floci (F11 fix); explicit keyword mapping; `search_after` cursor.
- `GET /v1/posts?search_keyword=` → OpenSearch; 503-degrades search only; was 501 in P1.
- Verified end-to-end on real AWS: write → Streams → Lambda (signed) → OpenSearch → searchable; indexing lag **1.89 s** (<10 s SLO).

### Caching + rate limiting (P2-DEV-04/05/06)
- `SingleFlightCache`: request coalescing + stale-while-revalidate + jittered TTL (herd guard, R12) — 10 concurrent misses → 1 load.
- Rate limiter **wired into write hot path** → 429 + Retry-After (fixed-window per user; in-memory dev / Redis prod). Verified real Redis (Valkey) on Floci + under load.
- DAX / ElastiCache / CloudFront modules built + gated (not load-tested to save cost; DAX not on Floci — F3).

## NFR / load testing
Real multi-user async harness (`tests/load`, `make nfr`), run on Floci + real AWS:
- Availability 100% non-5xx under concurrent load; read-your-own-write (ConsistentRead); rate-limit 429; search freshness 1.89 s.
- **Real in-region DynamoDB latency** (in-VPC Lambda, 512 MB, gateway endpoint, eu-central-1): **p50 5.1 ms / p95 13.4 ms / p99 15.0 ms** — ~10× inside the ≤150 ms read SLO.
- Documented honestly in `NFR_REPORT.md`: the earlier "seconds" latency was a laptop→AWS WAN artifact, then Lambda CPU starvation at 128 MB — never the system.

## Real-AWS findings (Floci could not surface)
- **F10**: WAFv2 cannot associate to API Gateway v2 (HTTP API) → P1 uses stage throttling; WAF reserved for CloudFront.
- **F11**: OpenSearch requires SigV4-signed requests (Floci accepts unsigned) → config-gated signing + domain access policy.
- GSI projections must include `postId` (list-latest `KeyError` on real AWS) → fixed both GSIs.
- OpenSearch domain policy must apply after the domain settles + roles exist (409 otherwise; converges on re-apply).
- Lambda memory = CPU: 128 MB starved the AWS SDK client (flat 40 ms); 512 MB → real single-digit ms. Account has a 512 MB Lambda cap.

## Region
Dev/Floci region-agnostic; prod default now **eu-central-1** (Frankfurt, closest to the Budapest developer). Full-app E2E passes in both us-east-1 and eu-central-1 — region is a one-line tfvars change.

## Deferred
- P3: subscriptions/feed + fan-out (D9-gated), full observability/DR.
- In-VPC Fargate load test against API Gateway for end-to-end SLO sign-off (data-plane latency already proven).
- DAX/ElastiCache/CloudFront load testing (modules ready; standing cost).
- `make scan` (pip-audit/gitleaks/semgrep) — CI.

## Verification snapshot
62 unit/api/contract tests + 7 Floci integration tests green; `make check` (lint + import-linter boundary) clean. Real-AWS stacks deployed, verified, and destroyed in both regions.
