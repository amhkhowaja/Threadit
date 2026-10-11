# Threadit — Phase 1 Completion Summary

> Status: **Phase 1 complete.** Verified on both environments — dev on Floci and prod on real AWS.
> Scope delivered per `PLANNING.md` §1 (P1-DEV-01..07, P1-INFRA-01..09) and the decisions in `ANALYSIS.md` (D1–D11) and `DEVELOPMENT_STRATEGY.md` (I1–I10).

## What Phase 1 delivers

A correct, future-proof, horizontally-scalable foundation for a message board architected for billions, built AWS-managed-service-first with thin Python/FastAPI services, dev-on-Floci / prod-on-real-AWS via one Terraform codebase.

### Functional (FR1–FR4, FR6)
- Create posts (title + body), threaded replies (materialized path, depth cap 8).
- Read a post, its comment tree (one query, thread-ordered) and lazy subtree by `rootCommentId`.
- List latest posts (GSI1 time-bucket) and a user's posts (GSI2).
- Durable persistence (DynamoDB single table `threadit`).
- Writes require Cognito JWT (API Gateway authorizer); reads public.
- `search_keyword` → defined `501` (OpenSearch is P2).

### Architecture / decisions enacted
- Single-table DynamoDB (AP, eventual consistency), Streams enabled for P2/P3 CQRS read models.
- Two thin FastAPI apps (`post_write`, `post_read`) + shared `threadit_core`; layered OOP (routers → use-cases → repository ports → pure domain); boto3 confined to one adapter (import-linter enforced).
- Idempotent writes (conditional `PutItem` + 24h TTL); mass-assignment guard (userId from token `sub`).
- Opaque cursor pagination; RFC 9457 problem+json errors; structlog JSON with redaction (no secrets/PII/tokens).
- Managed-first rate limiting: **API Gateway stage throttling** (WAFv2 cannot bind to HTTP APIs — see below).

## Verification evidence

| Gate | Result |
|------|--------|
| `make check` (ruff + import-linter boundary + unit/api/contract) | 39 tests passing, boundary KEPT |
| `make itest` (Floci real DynamoDB) | 4 integration tests passing (idempotency, threaded tree, GSI2) |
| `make tf-apply ENV=dev` (Floci) | 25 resources; `make smoke` E2E green (post + threaded reply + read + 501) |
| `make tf-apply ENV=prod` (real AWS) | clean **24 add → 24 destroy** cycle via Terraform |
| F1 least-privilege (real AWS) | read role = Query/GetItem, write role = Put/UpdateItem (confirmed on live policies) |
| Auth split (real AWS) | POST routes = JWT, GET routes = public |

## Real-AWS findings (would not surface on Floci)
- **F10 — WAFv2 ↔ API Gateway v2:** real AWS rejects associating a WAF web ACL to an HTTP API (Floci accepted it). Fixed: P1 uses API Gateway stage throttling; WAF retained for the CloudFront front in P2. Recorded in `FLOCI_AWS_SERVICES_COMPATIBILITY.md` §F10/§8b.
- Deployer IAM needs `iam:ListInstanceProfilesForRole` for clean Terraform destroys (documented §8a).

## Deferred (by design)
- **P2:** images (S3 presigned), caching (DAX/ElastiCache/CloudFront + WAF front), search (OpenSearch via Streams→Lambda).
- **P3:** subscriptions/feed + celebrity fan-out (gated on D9), full observability/DR.
- **Not yet wired:** `make scan` (pip-audit/gitleaks/semgrep — CI, scanners missing locally); ECR image push + full ECS container deploy (standing cost; disabled for the P1 verification runs).

## How to run
```
make install          # venv + pinned deps
make check            # lint + boundary + tests (no AWS)
make floci-up         # start pinned Floci emulator
make itest            # integration tests on Floci
make tf-apply ENV=dev # provision into Floci
make smoke            # end-to-end smoke
make tf-destroy ENV=dev
```
Prod: same with `ENV=prod` against real AWS (requires an authenticated deployer; see FLOCI doc §8a).
