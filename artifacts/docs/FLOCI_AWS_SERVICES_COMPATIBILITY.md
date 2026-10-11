# Threadit — FLOCI ↔ AWS SERVICES COMPATIBILITY

> Companion to `ANALYSIS.md`, `PLANNING.md`, `SYSTEM_ARCHITECTURE.md`.
> Status: Draft for review. Author: Senior System Architect.
> Purpose: define the **dev-on-Floci / prod-on-real-AWS** Terraform strategy for Threadit, and give an honest per-service compatibility matrix so we know exactly where the emulator is faithful and where it is not.
>
> **Sources (verified, not assumed):** Floci official README and the Floci Terraform getting-started guide (`github.com/floci-io/floci`), fetched 2026-10-10. Where Floci's own docs do not state operation-level support for a specific resource, this document marks it **[VERIFY]** rather than inventing certainty.
>
> **Governing caveat (Floci's own words):** *"an emulator is not AWS itself and cannot establish that an application will behave identically in production… local success is not proof of production parity."* Floci publishes ~2,576 automated compatibility tests across 5 SDKs and 3 IaC tools (incl. 67 Terraform tests), but a service appearing on its list does not mean every AWS operation/edge case is covered. **Prod behavior is always validated against real AWS in staging (PLANNING §5).**

---

## 1. What Floci is (grounded facts)

- A free, MIT-licensed, **local AWS emulator** (Docker image `floci/floci:latest`), a drop-in replacement for LocalStack Community.
- **Single endpoint:** everything is served at `http://localhost:4566`. Any published region works; credentials are any non-empty value (e.g. `test`/`test`) unless stricter per-service auth is enabled.
- **Works with the standard `hashicorp/aws` Terraform provider** (`~> 6.0`) — no custom provider. You point the provider's `endpoints {}` at `localhost:4566` and set the `skip_*` + `s3_use_path_style` flags.
- **Two execution models:**
  - **In-process** (stateless/stateful mocks): S3, DynamoDB + Streams, API Gateway REST & v2, Cognito, KMS, Secrets Manager, IAM/STS, WAF v2, CloudFront, Route53, ACM, ELB v2, Auto Scaling, CloudWatch Logs/Metrics, Step Functions, SNS/SQS, etc.
  - **Real Docker-backed** (higher fidelity): **Lambda, ECS, EC2, EKS, OpenSearch, ElastiCache (Valkey/Redis), RDS, MSK, CodeBuild, Managed Flink**. These need the Docker socket mounted (`/var/run/docker.sock`).
- **Persistence modes** via `FLOCI_STORAGE_MODE`: `memory` (CI/ephemeral), `persistent`, `hybrid`, `wal`. For a dev environment that should **survive restart** (FR4 locally), use `persistent`, `hybrid`, or `wal` — **not** the default `memory`.
- **S3-backed Terraform state + DynamoDB lock** are supported locally, so the full IaC workflow can run with zero cloud account.

---

## 2. Threadit service inventory → Floci compatibility matrix

Legend: **✅ In-process emulation** · **🐳 Real Docker-backed (high fidelity)** · **⚠️ Partial / verify operations** · **❌ Not emulated — needs a dev substitute** · **[VERIFY]** confirm the exact resource/operation before relying on it.

### 2.1 Phase 1 (foundation) services

| Threadit need | AWS service (prod) | Floci (dev) | Fidelity notes | Dev strategy |
|---------------|--------------------|-------------|----------------|--------------|
| Primary datastore (single table `threadit`) | **DynamoDB** | ✅ In-process | README states **GSI, LSI, Query, Scan, TTL, transactions, batch, Streams w/ shard iterators + Lambda event-source mapping**. Covers AP1–AP7, GSI1/GSI2, TTL on `IDEMPO#`, Streams-on. | Same `aws_dynamodb_table` HCL in dev & prod; dev uses `PAY_PER_REQUEST`. **[VERIFY]** PITR (`point_in_time_recovery`) acceptance — see §5. |
| Change feed (CQRS enabler) | **DynamoDB Streams** | ✅ In-process | Streams + shard iterators + Lambda ESM explicitly supported. No consumer in P1, so low risk. | Enable `stream_enabled` + `NEW_AND_OLD_IMAGES` identically. |
| Write/read request services | **ECS Fargate** | 🐳 Real Docker (ECS) | Floci ECS = clusters, task defs, tasks, services, capacity providers, task sets via **real containers**. **Fargate launch type specifics / networking is [VERIFY]** — Floci runs the task image on local Docker, not AWS-managed Fargate. | Run the two service containers via Floci ECS **or** (recommended for inner loop) plain `docker compose` + point the app at `localhost:4566`. Keep the `aws_ecs_*` HCL for prod parity; see §4 toggle. |
| Public API front door | **API Gateway (HTTP API / v2)** | ✅ In-process | v2 = HTTP APIs, routes, integrations, **JWT authorizers**, stages. Matches our Cognito-JWT-authorizer-on-writes design. **Note:** Floci's "API Gateway v2 / HTTP API" and "Cognito" are called out as advantages over LocalStack Community. | Same `aws_apigatewayv2_*` HCL. **[VERIFY]** JWT authorizer validation depth against Cognito JWKS locally. |
| Identity / auth | **Cognito (user pool)** | ✅ In-process | README: **user pools, app clients, auth flows, JWKS and OpenID well-known endpoints.** Enough to issue/validate JWTs locally. | Same `aws_cognito_user_pool*` HCL. **[VERIFY]** exact token claim shape vs prod; our authz uses `sub` → low risk. |
| Rate limiting (volumetric) | **WAF v2** | ✅ In-process (REGIONAL + CLOUDFRONT scopes) | Web ACLs, IP sets, regex sets, rule groups, logging, **resource associations**, tagging. Control-plane fidelity good; **actual rate-based rule *enforcement* under load is [VERIFY]** (emulated, not a real edge). | Create the ACL in both; **do not** rely on Floci to prove throttling behavior — load-test rate limits in staging. |
| Secrets / config | **Secrets Manager + SSM Parameter Store** | ✅ In-process | Secrets Manager: versioning, resource policies, tagging. SSM Parameter Store: versions, SecureString, tagging. | Same HCL; dev secrets are dummy values. |
| Encryption keys | **KMS** | ✅ In-process | Encrypt/decrypt/sign/verify, data keys, aliases. | Same `aws_kms_key` HCL; SSE-KMS on table/bucket works in dev. **[VERIFY]** envelope-encryption edge cases. |
| App roles / least privilege | **IAM + STS** | ✅ In-process | Users, roles, groups, policies, instance profiles; STS AssumeRole/WebIdentity. **Policy *evaluation* is largely permissive in emulators** — IAM denies are not a reliable local signal unless `FLOCI_SERVICES_S3_ENFORCE_AUTH`/strict modes are enabled. | Author real least-priv policies in HCL (prod needs them); **do not** treat "it worked in dev" as proof the policy is correct — verify authz in staging (R9). |
| Networking (VPC, subnets, endpoints) | **VPC / EC2 networking** | 🐳/⚠️ | EC2 is Docker-backed; **VPC resources exist but local networking is emulated, not enforced** (no real subnet isolation/NAT/VPC-endpoint routing). | Keep `aws_vpc`/subnet/endpoint HCL for prod; in dev these are effectively **no-ops for traffic** — the app just reaches `localhost:4566`. Flag as a parity gap (§6). |
| Baseline logs/metrics | **CloudWatch Logs/Metrics** | ✅ In-process | Log groups/streams/ingestion/filtering; custom metrics, alarms. | Same HCL; useful for local log capture. |
| Terraform state + lock | **S3 + DynamoDB** | ✅ In-process | Floci explicitly supports **S3 backend + DynamoDB lock** locally (used by its own compat suite). | Local S3 state bucket `tfstate` + `tflock` table in dev; real S3+DynamoDB backend in prod. |

### 2.2 Phase 2 services (images, caching, search)

| Threadit need | AWS service (prod) | Floci (dev) | Fidelity notes | Dev strategy |
|---------------|--------------------|-------------|----------------|--------------|
| Image storage (presigned PUT) | **S3** | ✅ In-process | **Versioning, multipart, pre-signed URLs, Object Lock, event notifications.** Presigned PUT is explicitly supported — our image-upload flow (ADR-007) works locally. | Same `aws_s3_bucket*` HCL; use `s3_use_path_style=true` in the provider. |
| Full-text search (read model) | **OpenSearch** | 🐳 Real Docker (`opensearchproject/opensearch:2`) | **Full OpenSearch engine with REST API**; domain CRUD, versions, instance types. High fidelity for query behavior. | Same `aws_opensearch_domain` HCL (dev = single small node). Real engine means search relevance tests are meaningful locally. |
| Stream→index pipeline | **Lambda** (Streams consumer) | 🐳 Real Docker (`public.ecr.aws/lambda/`) | Real runtime env, execution model, warm pool, aliases, Function URLs; **DynamoDB Streams → Lambda ESM supported**. High fidelity. | Same `aws_lambda_function` + `aws_lambda_event_source_mapping` HCL. Needs Docker socket. |
| Hot-item read cache | **DAX** | ❌ **Not in Floci's service list** | DAX is **not** listed among emulated services. | **Dev substitute:** skip DAX locally (read service talks straight to DynamoDB) **or** use the Floci ElastiCache (Valkey) as a stand-in only for cache *plumbing* tests. DAX itself is prod-only. Flag (§6). |
| Counters / rate-limit state / cache | **ElastiCache (Redis)** | 🐳 Real Docker (`valkey/valkey:8`) | **Real Redis/Valkey protocol**, ACL-based IAM auth, SigV4 validation. High fidelity for our counter + rate-limit-state use. | Same `aws_elasticache_*` HCL (dev = single node). Real Redis means counter logic is faithfully testable. |
| Edge cache / CDN / image delivery | **CloudFront (+ OAC)** | ✅ In-process (control plane) | Distributions, origins, cache behaviors, invalidations, tagging. **Control-plane only** — Floci is not a real global edge; **actual edge caching/latency is not emulated.** | Keep `aws_cloudfront_distribution` HCL for prod; in dev, read the origin (API GW/S3) directly. OAC config is created but edge behavior is prod-validated. Flag (§6). |
| Per-client throttling | **API Gateway usage plans** | ⚠️ [VERIFY] | API GW v2 supported; **usage-plan/quota enforcement depth is [VERIFY]**. | Create plans in HCL; verify enforcement in staging. |

### 2.3 Phase 3 services (feed/fan-out — conditional D9; observability/DR)

| Threadit need | AWS service (prod) | Floci (dev) | Fidelity notes | Dev strategy |
|---------------|--------------------|-------------|----------------|--------------|
| Fan-out workers (if D9=feed) | **Lambda** on Streams | 🐳 Real Docker | As §2.2. | Same HCL. |
| Feed projection store (if D9=feed) | **DynamoDB** (separate items/table) | ✅ In-process | As §2.1. | Same HCL. |
| Distributed tracing | **AWS X-Ray / OTel** | ⚠️/[VERIFY] | X-Ray is **not** on Floci's listed services. | Use an **OTel collector container** locally (vendor-neutral) rather than X-Ray; prod can use X-Ray or managed OTel. Flag (§6). |
| Metrics/alerting (SLO burn) | **CloudWatch (+ Managed Prometheus)** | ⚠️ control plane; no real alarm firing | CloudWatch metrics/alarms + AMP listed; **alarm *actions* are emulated**. | Validate alarm *definitions* locally; validate firing/notification in staging. |
| DR / PITR restore drill | **DynamoDB PITR / AWS Backup** | ⚠️ [VERIFY] | AWS Backup is in-process (simulated job lifecycle); DynamoDB PITR acceptance is [VERIFY]. | DR drills are a **real-AWS/staging** activity (P3-INFRA-A3), not a Floci activity. |

---

## 3. Summary: where dev (Floci) is trustworthy vs where it is not

**High-fidelity on Floci (safe to build/test the behavior locally):**
- DynamoDB single-table incl. GSIs, TTL, transactions, **Streams→Lambda** (the core of P1 + the CQRS enabler).
- S3 incl. **presigned URLs** (image upload path, P2).
- **OpenSearch** (real engine) and **ElastiCache/Valkey** (real Redis) — search + counters test meaningfully.
- Lambda (real runtime), Cognito (JWKS/OIDC), API Gateway v2 JWT authorizer, KMS, Secrets Manager, SSM.

**Control-plane only / NOT a behavioral proof on Floci (must verify in real-AWS staging):**
- **CloudFront** edge caching & latency — emulated control plane only.
- **WAF** rate-based *enforcement* under load.
- **API Gateway usage-plan** throttling enforcement.
- **IAM policy denies / least-privilege correctness** — emulators are permissive by default (R9).
- **VPC network isolation / NAT / VPC endpoints** — not enforced locally.
- **PITR / DR restore**, CloudWatch **alarm firing**.

**Not emulated — needs a dev substitute or is prod-only:**
- **DAX** → skip in dev (go direct to DynamoDB) or substitute ElastiCache for plumbing only.
- **X-Ray** → use a local OTel collector instead.

---

## 4. Terraform strategy: one codebase, two environments

**Principle (consistent with PLANNING §5):** *same modules everywhere; only the provider endpoints, capacity parameters, and a few `enable_*` toggles differ.* No forked HCL for dev vs prod.

### 4.1 Provider wiring (the only hard dev/prod split)

Dev points every service endpoint at Floci; prod uses the default AWS endpoints.

```hcl
# variables.tf
variable "use_floci" {
  type        = bool
  default     = false   # prod default = real AWS
  description = "When true, target the local Floci emulator at localhost:4566."
}
variable "floci_endpoint" {
  type    = string
  default = "http://localhost:4566"
}

# provider.tf
provider "aws" {
  region = var.region

  # --- Floci-only settings (ignored/harmless in prod because toggled) ---
  access_key                  = var.use_floci ? "test" : null
  secret_key                  = var.use_floci ? "test" : null
  skip_credentials_validation = var.use_floci
  skip_metadata_api_check     = var.use_floci
  skip_requesting_account_id  = var.use_floci
  s3_use_path_style           = var.use_floci

  dynamic "endpoints" {
    for_each = var.use_floci ? [1] : []
    content {
      dynamodb       = var.floci_endpoint
      s3             = var.floci_endpoint
      apigatewayv2   = var.floci_endpoint
      cognitoidp     = var.floci_endpoint
      kms            = var.floci_endpoint
      secretsmanager = var.floci_endpoint
      ssm            = var.floci_endpoint
      iam            = var.floci_endpoint
      sts            = var.floci_endpoint
      logs           = var.floci_endpoint
      wafv2          = var.floci_endpoint
      cloudfront     = var.floci_endpoint
      ecs            = var.floci_endpoint
      ec2            = var.floci_endpoint
      elasticache    = var.floci_endpoint
      lambda         = var.floci_endpoint
      opensearch     = var.floci_endpoint
    }
  }
}
```

> **Important:** Floci requires an endpoint entry **for every service the configuration touches** (its Terraform doc states this explicitly). Keep the `endpoints {}` list in sync with the services actually used per phase.

### 4.2 Capability toggles for parity gaps

Services Floci can't faithfully run (DAX, X-Ray) or that are pointless locally (CloudFront edge, VPC traffic enforcement) are gated so dev skips them without changing prod:

```hcl
variable "enable_dax"        { type = bool, default = true }   # false in dev tfvars
variable "enable_cloudfront" { type = bool, default = true }   # created-but-bypassed in dev
variable "enable_xray"       { type = bool, default = true }   # false in dev (use OTel locally)

# e.g.
resource "aws_dax_cluster" "read_cache" {
  count = var.enable_dax ? 1 : 0
  # ...
}
```

- `envs/dev.tfvars`: `use_floci = true`, `enable_dax = false`, `enable_xray = false`, on-demand/single-node capacity.
- `envs/prod.tfvars`: `use_floci = false`, everything enabled, provisioned + autoscaling + multi-AZ.

### 4.3 Remote state
- **Dev:** Floci-backed S3 state + DynamoDB lock (`tfstate` bucket, `tflock` table at `localhost:4566`), or a plain local backend for the fastest inner loop.
- **Prod:** real S3 + DynamoDB-lock backend with encryption and versioning.

### 4.4 Compute inner loop
For day-to-day dev, running the two Fargate services as **plain `docker compose` containers** pointed at `http://floci:4566` (via `FLOCI_HOSTNAME=floci`, per README multi-container note) is faster than driving Floci ECS. The `aws_ecs_*` HCL still exists and is exercised in staging against real AWS. **[DECISION POINT]** confirm this inner-loop choice vs. always going through Floci ECS.

### 4.5 Local persistence (so dev survives restart — FR4 locally)
Set `FLOCI_STORAGE_MODE=persistent` (or `hybrid`/`wal`) and bind-mount `./data:/app/data`. The default `memory` mode loses all data on restart and must not be used when demonstrating FR4 locally.

---

## 5. Known compatibility risks & how we handle them

| ID | Area | Risk | Handling |
|----|------|------|----------|
| F1 | **IAM least-privilege** | Emulator is permissive; a wrong policy "passes" in dev | Treat IAM correctness as **staging-verified only** (R9); run authz negative tests against real AWS before prod. |
| F2 | **CloudFront / WAF edge behavior** | Caching, invalidation, rate-limit enforcement, latency not real locally | Validate cache hit-ratio, 429 throttling, and latency SLOs in **real-AWS staging** load tests (PLANNING §2.3, P2-INFRA-07). |
| F3 | **DAX absent** | No local DAX | Dev read path goes **direct to DynamoDB**; DAX enabled only in prod/staging via `enable_dax`. |
| F4 | **VPC/network isolation** | No real subnet/NAT/endpoint enforcement locally | Network/security posture validated in staging; dev treats networking as a no-op. |
| F5 | **PITR / DR** | Backup/restore semantics simulated | DR drill (P3-INFRA-A3) runs against real AWS, never Floci. |
| F6 | **Operation-level gaps** | A specific DynamoDB/API-GW/Cognito call may be partially implemented | Keep `[VERIFY]` items in §2; cross-check against Floci's live **Services Overview** (`floci.io/floci/services/`) for the pinned Floci version; CI runs the Terraform plan+apply against Floci to catch drift early. |
| F7 | **Fargate ≠ local Docker** | ECS tasks run on local Docker, not managed Fargate (networking/metadata differ) | Prod/staging run real Fargate; parity validated in staging smoke tests. |
| F8 | **Version drift** | Floci releases 1st & 3rd Tuesday; behavior can change | **Pin the Floci image** (`floci/floci:x.y.z`) in dev compose and CI; upgrade deliberately. |
| F9 | **False confidence** | "It worked on Floci" ≠ prod-correct | Policy: no feature is "done" until its exit criteria pass in **real-AWS staging** (PLANNING exit criteria). Floci accelerates the inner loop; staging is the source of truth. |
| F10 | **WAFv2 ↔ API Gateway v2 (CONFIRMED on real AWS)** | Floci **accepted** `aws_wafv2_web_acl_association` to an HTTP API; **real AWS rejected it** (`WAFInvalidParameterException`) — WAFv2 associates only to ALB / API GW **REST** / AppSync / Cognito, **not HTTP APIs**. Classic F2 false-positive. | **Fixed:** removed the association; P1 volumetric limiting = **API Gateway stage throttling** (rate/burst on `$default`). WAF ACL retained for the **CloudFront** front in P2. Verified: control plane deploys clean on real AWS without the association. |

---

## 6. Parity gap register (dev-only compromises, explicit)

| Component | Prod (real AWS) | Dev (Floci) | Compromise accepted |
|-----------|-----------------|-------------|---------------------|
| Read cache | DAX in front of DynamoDB | none (direct DynamoDB) | No local cache-hit testing; logic flagged for staging |
| CDN | CloudFront edge + OAC | control plane only / direct origin | No local edge/latency testing |
| Rate limiting | WAF + usage plans enforced at edge | ACL/plan created, not enforced | Throttling behavior staging-only |
| Tracing | X-Ray / managed OTel | local OTel collector | Different backend; spans still produced |
| Network | VPC, private subnets, VPC endpoints, NAT | emulated no-op | No local isolation guarantee |
| Compute | ECS Fargate (managed) | ECS-on-local-Docker or compose | Runtime/metadata differences |
| Durability | DynamoDB managed + PITR | `persistent`/`wal` disk mode | Restore semantics not identical |

---

## 7. Developer quick start (dev-on-Floci)

```bash
# 1. Start Floci with persistence + Docker socket (needed for Lambda/ECS/OpenSearch/ElastiCache)
cat > compose.yaml <<'YAML'
services:
  floci:
    image: floci/floci:1.5.x          # PIN the version (F8)
    ports: ["4566:4566"]
    environment:
      - FLOCI_STORAGE_MODE=persistent   # survive restart (FR4 locally)
      - FLOCI_HOSTNAME=floci            # correct returned URLs for app containers
    volumes:
      - ./data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock
YAML
docker compose up -d

# 2. Create Terraform remote-state backend resources in Floci (optional)
aws --endpoint-url http://localhost:4566 s3api create-bucket --bucket tfstate
aws --endpoint-url http://localhost:4566 dynamodb create-table \
  --table-name tflock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# 3. Apply Threadit infra against Floci
terraform init
terraform apply -var-file=envs/dev.tfvars    # use_floci=true, enable_dax=false, enable_xray=false

# 4. Verify
aws --endpoint-url http://localhost:4566 dynamodb list-tables
# → expect: threadit
```

Prod is identical commands with `-var-file=envs/prod.tfvars` and no `endpoints{}` override.

---

## 8. Open decision points
- **[DP-F1]** Inner-loop compute: Floci ECS vs plain `docker compose` for the two services (§4.4). *Recommendation: compose for inner loop, ECS HCL exercised in staging.*
- **[DP-F2]** Pin a specific Floci version for the team (§5 F8). *Recommendation: pin and upgrade on a schedule.*
- **[DP-F3]** Confirm the `[VERIFY]` operation-level items in §2 against the Floci Services Overview for the pinned version (PITR, API-GW usage-plan enforcement, Cognito token claim shape, KMS envelope edge cases) before P1 exit.
- **[DP-F4]** Whether to attempt any CloudFront/WAF behavior in a thin real-AWS "staging-lite" earlier than P2 to de-risk F2.

---

## 8a. Real-AWS deployer IAM policy requirements

The deploy IAM user (e.g. `threadit-deployer`) needs these action groups for a clean P1 `terraform apply`/`destroy` on real AWS: `dynamodb:*`, `cognito-idp:*`, `apigateway:*` (HTTP APIs authorize under `apigateway`, **not** `apigatewayv2`), `wafv2:*`, `ec2:*`, `ecs:*`, `logs:*`, `application-autoscaling:*`, and IAM role management (`CreateRole/DeleteRole/GetRole/PassRole/TagRole/UntagRole/ListRoles/PutRolePolicy/DeleteRolePolicy/GetRolePolicy/AttachRolePolicy/DetachRolePolicy/ListRolePolicies/ListAttachedRolePolicies`).

**Also required for a clean Terraform *destroy*** (the AWS provider calls these during role deletion / verification), learned from the real-AWS run:
- `iam:ListInstanceProfilesForRole` — the provider calls this before deleting a role; without it, role deletion fails and roles must be cleaned up manually.
- `iam:SimulatePrincipalPolicy` (optional) — only if you want to run live least-privilege simulations as F1 evidence.

## 8b. Real-AWS verification record (P1)

Deployed the P1 control plane to real AWS (account `453168420187`, `us-east-1`), verified, and destroyed. Confirmed:
- DynamoDB `threadit`: ACTIVE, Streams `NEW_AND_OLD_IMAGES`, SSE ENABLED, GSI1+GSI2.
- API Gateway: `POST` routes = JWT (Cognito authorizer), `GET` routes = public — correct FR6/D6 split.
- **F1 (Floci cannot prove):** read role scoped to `Query`/`GetItem`, write role to `PutItem`/`UpdateItem` — least-privilege confirmed from the live inline policy documents.
- API Gateway stage throttling live (rate 2000 / burst 1000).
- **F10 fix validated:** control plane applies clean without the (invalid) WAF→HTTP-API association.
- Teardown confirmed the account clean across all services.

### 8c. Real-AWS verification record (P2 search/images)

Partial real-AWS run (account `453168420187`, `us-east-1`), then torn down:
- **P2 Terraform is real-AWS-valid:** SQS DLQ, S3 image bucket (private, SSE-KMS, versioned), indexer IAM role (least-priv: Streams read + SQS send + logs), and the OpenSearch domain all began creating cleanly with real credentials/provider — no config errors.
- **Not observed on real AWS:** Lambda function + event-source-mapping wiring, because Terraform must wait on the OpenSearch endpoint and a real `t3.small.search` domain takes **10–20 min** to become available (confirmed twice). This is an AWS timing constraint, not a config problem.
- **Covered elsewhere:** the Stream→index→search *behavior* is proven against a **real OpenSearch engine** on Floci (3 integration tests: adapter upsert/search/delete, indexer e2e, search endpoint). The real-AWS gap is only the managed-ESM plumbing (standard wiring, no custom logic).
- **Lesson (operational):** if a long OpenSearch apply is interrupted, the domain is **not yet in Terraform state** → it becomes an **orphan**. Must be deleted directly (`aws opensearch delete-domain`) — a plain `terraform destroy` won't remove it. Recommendation for real-AWS P2: provision OpenSearch in a **separate apply/stage** ahead of the Lambda, or use a `-target` first, so the long-running resource doesn't block (and isn't orphaned by) the rest.

---

## 9. Bottom line
Floci is a strong fit for Threadit's **dev** environment: the **data core (DynamoDB + Streams), S3 presigned uploads, OpenSearch, ElastiCache, Lambda, Cognito, and API Gateway v2** — the services that carry our actual business logic — are either faithfully emulated in-process or run as **real Docker engines**, so most of P1 and P2 behavior is testable locally at zero cost with the same Terraform. The emulator is **not** a substitute for AWS on **edge/CDN, WAF enforcement, IAM authorization, VPC isolation, DAX, and DR** — those remain **real-AWS/staging-verified** (PLANNING §5). We adopt a single Terraform codebase with a `use_floci` provider toggle and `enable_*` capability flags, pin the Floci version, and treat **staging on real AWS as the source of truth for production readiness.**
