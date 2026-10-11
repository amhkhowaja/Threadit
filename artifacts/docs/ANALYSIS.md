# Threadit — ANALYSIS

> Document 1 of 3 (**ANALYSIS** → PLANNING → SYSTEM_ARCHITECTURE).
> Status: Draft for review. Author: Senior System Architect (orchestrating DB / API / Security specialists).
> Purpose: faithfully restate the requirements and the user's mental model, then deliver an honest senior critique — validating what is right, challenging what is questionable, and proposing better alternatives where they exist.
> Golden rule used throughout: ***"billions" is a capacity ceiling, not a day-1 bill.*** The design must be *correct and future-proof* now, while deferring cost and moving parts until a phase justifies them.
> Convention: genuine judgment calls that need your input are tagged **[DECISION POINT]** and collected as **D1–D11** at the end.

---

## 1. Requirements restated (faithful)

### 1.1 Functional
- **FR1** Create posts (title + body minimum).
- **FR2** Reply to posts (threaded or flat — our choice to recommend).
- **FR3** View a list of posts; view a single post with its replies.
- **FR4** Persistence survives restart (a real database).
- **FR5** *(later phase)* Upload an image as part of post body.
- **FR6** All **writes require auth**; **reads are public** at this stage.

### 1.2 Non-functional
- Scale: **billions** of users reading posts/comments and writing posts, **no downtime**.
- **Commenting is write-heavy; reading posts/replies is read-heavy** → user proposes CQRS.
- Priorities: High Availability, Scalability, Low Latency, Intense throughput, Partition tolerance, Resilience, **caching** for latency, **rate limiting** against throughput/DoS on a single op class (e.g. reads), horizontally-scalable + future-proof DB schema.
- CAP tradeoff: **AP** chosen; strong consistency not prioritized; **eventual consistency acceptable**.
- **TBD** subscriber list / feed — the celebrity problem (50M subscribers → expensive reads, slow writes).

### 1.3 Tech-stack intent
- Use **AWS managed services**; minimize implementation complexity; infra via **Terraform**.
- **DynamoDB** for high-throughput writes + horizontal scaling.
- **S3** for images (TBD).
- **ElastiCache** for region-based caching (phase 2, TBD).
- **CloudFront + WAF** for caching, rate limiting, image delivery, "auth".
- **Fargate** for service deployment.
- **Same codebase deployed twice** (read role + write role) to balance load "via CQRS".

### 1.4 The user's mental model (from the handwritten brainstorming — authoritative)
- Front door (**API Gateway / LB / caching / rate limiting / auth**) → **Post Service (reads)** and **Post Service (writes)**; both talk to **DynamoDB** and **S3**; a cache-miss path is drawn; **ElastiCache per region** is a TBD.
- **Post** fields: `timestamp, title, post-content {text, attachment}, comments[], id, user-id, user-subscriber`.
- **Comment** fields: `text, timestamp, attachment, comment-parent-id, user-id, id`.
- Endpoints sketched: `POST /post`, `POST /posts/{post_id}/comment`, `GET /posts` (pagination limit/offset → cursor; filters `last=5/10/20`, `user_id`, `search_keyword`), `GET /posts/{post_id}`, `GET /posts/{post_id}/comments`.
- Celebrity strategy sketched: **low subscriber count → push / fan-out-on-write**; **millions → pull / fan-out-on-read**.

**Overall:** this is a strong, well-above-average mental model. The instincts (NoSQL for write scale, CQRS split, edge caching, rate limiting, AP/eventual consistency, push/pull hybrid) are the *right vocabulary*. The critique below sharpens where the wording hides a trap or an over-build.

---

## 2. What is right (validated)

- **AP + eventual consistency for a public message board.** Correct. Readers tolerating a few seconds of staleness is the right trade for availability and scale. (See the honesty caveat in §3.7.)
- **DynamoDB for write-heavy + horizontal scale.** Correct, *provided* keys are access-pattern-driven and hot partitions are engineered out (§3.2). DynamoDB auto-partitions and gives predictable single-digit-ms key access.
- **Edge caching + rate limiting + WAF at the front door.** Correct layering for a read-heavy public workload.
- **S3 for images via a later phase.** Correct and appropriately deferred.
- **Fargate for stateless services.** Correct — managed, autoscaling, low-ops.
- **Push/pull hybrid awareness.** Correct *conceptually*; the critique is about *whether it belongs in v1 at all* (§3.8).
- **Phasing the TBDs.** Correct — images, caching, search, subscriptions should not block v1.

---

## 3. Honest critique & better alternatives

### 3.1 "Deploy the same codebase twice (read/write) = CQRS" — **challenge** → **[D1]**
Deploying one application as two autoscaling groups gives **load isolation and independent scaling/IAM** — genuinely useful — but it is **not CQRS**. CQRS separates the **read and write models/stores**, not two copies of the same app over the **same** table.
- **Correct interpretation:** call the P1 split **read/write *service separation*** over one DynamoDB write model. It is "good enough" and recommended for v1.
- **True CQRS** arrives when a read genuinely needs a *different model*: **search** (OpenSearch) and **feed** (projection), both fed asynchronously by **DynamoDB Streams**. We enable Streams in P1 (no table change later) but attach no consumer until P2/P3.
- **Decision D1:** adopt the honest naming (service separation now; Streams→read-models later).

### 3.2 DynamoDB key design — the real risk is **hot partitions**, not table count → **[D2]**
A naive partition key (e.g. a single "latest posts" partition, or `POST#<id>` for a viral post's comments) **hot-spots** and throttles at billions scale. Single-table vs multi-table is secondary; **access-pattern-driven keys** are what matter.
- **Latest-posts read** must not hinge on one monotonic partition → use **time-bucketed GSI** (`BUCKET#<yyyymmddhh>`) so "newest N" fans across hourly partitions.
- **Viral-post read storm** → absorbed at the **cache tier** (DAX/CloudFront), not by key redesign.
- **Single-post comment-write storm** → optional **write-sharding** (`POST#<id>#<shard>` + scatter-gather), designed-for but **off by default**.
- **Recommendation:** single-table design, keys driven by the access-pattern catalog (AP1–AP7 in the architecture doc). **Decision D2:** approve access-pattern-driven single-table modeling.

### 3.3 Threaded replies — **threaded via materialized path, in v1** → **[D3]** *(decided — the product is "Threadit")*
The product name implies threading, so **threaded (nested) replies are in scope for v1**. The naive risk — recursive/N+1 reads of a comment tree — is avoided by choosing the right encoding, **not** an adjacency list.
- **Decision:** **threaded replies via materialized path.** Each comment stores a sortable path in its sort key: `COMMENT#<rootTs>#<...ancestors>#<ownTs>#<commentId>`. A single `Query` with `SK begins_with "COMMENT#"` returns the **entire comment tree in thread order in one round trip**; `SK begins_with "COMMENT#<rootPath>"` returns a **single subtree** for lazy "load more replies." No recursion; stays within DynamoDB's sort-key-range strength.
- **Active fields** (previously reserved): `parentId` (null = top-level reply), `depth` (int), `rootCommentId` (top-level ancestor, for paging top-level threads then lazy-loading subtrees).
- **Tradeoffs (honest):** paths are **immutable** (no cheap re-parenting — fine for a board); items are slightly larger; a **max depth cap is required** or paths/UI grow unbounded. Still fully **AP / eventually consistent** — no CAP change.
- **Sub-decisions (defaults applied, confirm if you disagree):**
  - **Max nesting depth = 8**; beyond that the UI shows "continue this thread" (lazy subtree load). *(recommended default applied)*
  - **Default read shape:** return the **full tree up to a per-post comment limit**, then **lazy-load deep subtrees** on demand. *(recommended default applied)*
- **D3 (now decided):** threaded via materialized path, depth cap 8, full-tree-then-lazy-subtree. Supersedes the earlier flat-v1 recommendation.

### 3.4 The "both services hit the same DynamoDB" read model — **sharpen**
The sketch is fine for v1, but it means **reads are eventually consistent against the write model**. That is acceptable (AP) *except* for a user re-reading their own just-created post/comment (§3.7). The read service should **not** try to serve `search_keyword` from DynamoDB.

### 3.5 Search is a real gap → **[D4]**
`GET /posts?search_keyword=` **cannot be served efficiently by DynamoDB** (no full-text; a scan is unbounded cost). This is the one place the mental model hand-waves.
- **Recommendation:** **OpenSearch** as a true CQRS read model (P2), async-indexed via **Streams → Lambda** (idempotent, DLQ).
- In P1 the endpoint is **declared** but returns a defined **501 "search not yet available"**, so the contract never changes.
- **Decision D4:** approve OpenSearch for search in P2 (and the P1 501 placeholder).

### 3.6 Caching tiers & invalidation — **clarify what each is for** → **[D5]**
"ElastiCache for region-based caching" conflates three different jobs:
- **CloudFront** — edge cache for **public GET** responses and image delivery.
- **DAX** — in front of DynamoDB for **hot item/query** reads (DynamoDB-native).
- **ElastiCache (Redis)** — **approximate counters** (comment counts) and **rate-limit state**, not primary read caching.
Under eventual consistency, prefer **short jittered TTL expiry over precise invalidation**, with **single-flight / stale-while-revalidate** to prevent a **thundering herd** on a hot post's cache expiry. **Decision D5:** approve the three-tier model (all in P2).

### 3.7 CAP/AP is right, but **read-your-own-write** needs honesty → **[D7]**
Users *expect* to see their own just-posted content immediately. Pure eventual consistency breaks that expectation and reads as a bug.
- **Recommendation:** return the **canonical representation on write** (optimistic UI), and offer a **narrow `ConsistentRead`** path for the author's own re-fetch (`GET /v1/posts/{id}?consistent=true`). Everything else stays eventual.
- **Decision D7:** approve the narrow read-your-own-write exception; keep all other reads eventual.

### 3.8 Celebrity/fan-out — **challenge whether a feed belongs in v1 at all** → **[D9]**
The 50M-subscriber "celebrity problem" **only exists if Threadit has a per-user feed**. A classic **message board** often needs only a **shared board list** (newest/active threads), which the time-bucketed GSI already serves — **no fan-out, no subscriber graph**.
- Building push/pull fan-out and a subscriber graph in v1 is a **large cost/complexity bet on an unconfirmed feature**.
- **Recommendation:** **defer entirely to P3**, gated on **D9**. If D9 = "shared board list," fan-out is **not built**; the `user-subscriber` field does **not** enter v1. If D9 = "personalized feed," build the **hybrid push (normal) + pull (celebrity)** on a Streams-fed projection.
- **Decision D9 is the single biggest scope lever in the whole design.**

### 3.9 "CloudFront does auth" — **correct the layer** → **[D6]**
CloudFront/WAF do **edge caching, TLS, and volumetric defense** — **not identity**. Auth belongs to:
- **Amazon Cognito** (OIDC user pool) issuing JWTs,
- **API Gateway JWT authorizer** validating on **write** routes,
- **service-level resource authz** ("write only as yourself" — `userId` from the **token**, never the body) to prevent **IDOR/BOLA** and **mass assignment**.
- **Decision D6:** approve Cognito + API Gateway authorizer; reads public.

### 3.10 Rate limiting — **make it layered** → **[D8]**
Protect the read class from abuse without starving writes:
- **WAF rate-based rules** (coarse, volumetric, P1),
- **API Gateway usage plans/quotas** (per-client/tier, P2),
- **ElastiCache-backed app counters** (fine-grained, P2),
- return **429 + `Retry-After`**.
- **Decision D8:** approve defense-in-depth rate limiting.

### 3.11 Images — **presigned S3, never proxy bytes** → **[D11 compute note]**
Server must not stream large binaries. Use **presigned S3 PUT** direct from client; store the object key in the reserved `attachment` field; serve via **CloudFront OAC from a private bucket**. (P2.)

### 3.12 Compute split → **[D11]**
Request services on **Fargate** (long-lived, autoscaled); **Streams consumers** (search indexer, future fan-out) on **Lambda** with DLQs. **Decision D11:** approve Fargate (request) + Lambda (async).

### 3.13 Single-region vs multi-region → **[D10]**
Billions of users with "no downtime" *implies* multi-region eventually, but multi-region DynamoDB (global tables) + active-active is a large cost/complexity step.
- **Recommendation:** **single-region multi-AZ** for v1 (meets ~99.95%); treat **multi-region as deferred**, revisited only if the availability SLO is raised to 99.99% (§3.14).
- **Decision D10:** confirm single-region multi-AZ for v1; multi-region deferred.

### 3.14 Cost & operational honesty at "billions"
Always-on OpenSearch, DAX, ElastiCache, NAT gateways, and Streams consumers are **real recurring cost**. The phased plan exists precisely so spend tracks adoption. A cost dashboard with per-service line-items and VPC endpoints (over NAT) are recommended from P1.

---

## 4. Summary of recommendations
1. P1 = read/write **service separation** (not CQRS); enable Streams for later read-models. **(D1)**
2. **Single-table DynamoDB**, access-pattern-driven keys, time-bucketed latest-posts GSI, optional comment write-sharding. **(D2)**
3. **Threaded replies via materialized path** in v1 (depth cap 8, full-tree-then-lazy-subtree); `parentId`/`depth`/`rootCommentId` active. **(D3)**
4. **OpenSearch** for search (P2); P1 declares the endpoint, returns 501. **(D4)**
5. **Three-tier caching** (CloudFront/DAX/ElastiCache), TTL-expiry + herd guards (P2). **(D5)**
6. **Cognito + API Gateway authorizer**; resource-level authz; reads public. **(D6)**
7. **Narrow read-your-own-write** exception; all other reads eventual. **(D7)**
8. **Layered rate limiting** (WAF → usage plans → app counters). **(D8)**
9. **Defer subscriptions/feed/fan-out to P3, gated on D9** — a board may need no feed at all.
10. **Single-region multi-AZ** v1; multi-region deferred. **(D10)**
11. **Fargate (request) + Lambda (async stream)**; presigned S3 for images. **(D11)**

---

## 5. Key decisions I need confirmation on (D1–D11)

| ID | Decision | Default recommendation | Blocks |
|----|----------|------------------------|--------|
| **D1** | Name the read/write split honestly (service separation, not CQRS) | Yes | ADR-002 |
| **D2** | Access-pattern-driven single-table DynamoDB | Yes | Data model, P1 |
| **D3** | **Threaded replies via materialized path** in v1 (depth cap 8; `parentId`/`depth`/`rootCommentId` active) | **Yes — decided (product is "Threadit")** | ADR-003, API, data model |
| **D4** | Search via OpenSearch in P2; P1 returns 501 placeholder | Yes | ADR-004, P2 |
| **D5** | Three-tier caching (CloudFront/DAX/ElastiCache), P2 | Yes | ADR-005, P2 |
| **D6** | Cognito + API GW authorizer (auth is NOT at CloudFront) | Yes | ADR-006, P1 |
| **D7** | Narrow read-your-own-write (ConsistentRead) exception | Yes | ADR-005/007, UX |
| **D8** | Layered rate limiting (WAF + usage plans + app counters) | Yes | ADR-008 |
| **D9** | **Personalized feed vs shared board list** — does v1/the product need a per-user feed and subscriber graph at all? | **Shared board list (no fan-out)** | **ADR-009, all of P3 Track B** |
| **D10** | Single-region multi-AZ v1; multi-region deferred | Yes | ADR-010, SLO, DR |
| **D11** | Fargate (request) + Lambda (async); presigned S3 for images | Yes | ADR-007/010 |

**D9 is the most important** — it determines whether a large, expensive subsystem is built at all. My recommendation is to ship v1 as a shared board list and only add a personalized feed if the product genuinely requires one.
