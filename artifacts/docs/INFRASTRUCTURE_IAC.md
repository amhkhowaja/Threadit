# Threadit — Infrastructure as Code (Terraform) Reference

> A reader's guide to the Terraform that provisions Threadit. Covers the provider
> model (one codebase, Floci vs real AWS), the capability-flag system, a dependency
> diagram, and **every parameter of every module** with its value and rationale.
> Source of truth: `terraform/` (this doc is generated from it by hand and kept in sync).

---

## 1. Provider model — one codebase, two targets

Threadit uses a single Terraform codebase for both the local Floci emulator (dev) and
real AWS (prod), switched by `var.use_floci`.

```hcl
# terraform/main.tf
provider "aws" {
  region                      = var.region
  access_key                  = var.use_floci ? "test" : null   # dummy creds for Floci
  secret_key                  = var.use_floci ? "test" : null
  skip_credentials_validation = var.use_floci
  skip_metadata_api_check     = var.use_floci
  skip_requesting_account_id  = var.use_floci
  s3_use_path_style           = var.use_floci                   # Floci S3 needs path-style
  dynamic "endpoints" {                                         # when Floci: point every
    for_each = var.use_floci ? [1] : []                         # service at localhost:4566
    content { dynamodb = var.floci_endpoint ; s3 = var.floci_endpoint ; ... }
  }
}
```

Required providers: `hashicorp/aws ~> 6.0`, `hashicorp/archive ~> 2.4` (zips Lambda
packages). Terraform `>= 1.9`.

```
┌─────────────────────────────┐        ┌─────────────────────────────┐
│  dev   (use_floci = true)   │        │  prod  (use_floci = false)  │
│  endpoints -> :4566 (Floci) │        │  real AWS service endpoints │
│  dummy creds, path-style S3 │        │  real creds, SigV4 signing  │
└──────────────┬──────────────┘        └──────────────┬──────────────┘
               └──────────────  same modules  ─────────┘
```

---

## 2. Capability flags (root `variables.tf`)

Which modules instantiate is controlled by `enable_*` flags, so one codebase serves
control-plane, full-prod-web, and cost-bounded verify profiles.

| Variable | Type | Default | Purpose |
|---|---|---|---|
| `region` | string | `us-east-1` | target AWS region |
| `use_floci` | bool | `false` | target the Floci emulator |
| `floci_endpoint` | string | `http://localhost:4566` | Floci URL (dev) |
| `name_prefix` | string | `threadit-dev` | prefix for all resource names |
| `table_name` | string | `threadit` | DynamoDB table name |
| `ddb_billing_mode` | string | `PAY_PER_REQUEST` | DynamoDB capacity mode |
| `enable_dax` | bool | `true` | provision DAX read cache |
| `enable_cloudfront` | bool | `true` | S3 image CloudFront OAC bits |
| `enable_xray` | bool | `true` | (reserved) tracing |
| `enable_ecs` | bool | `true` | legacy ECS module (superseded by `ecs_alb`) |
| `service_image` | string | `threadit:local` | container image for the services |
| `enable_search` | bool | `true` | OpenSearch domain + Streams→Lambda indexer |
| `enable_elasticache` | bool | `true` | ElastiCache (Redis) for rate-limit state |
| `enable_loadgen` | bool | `false` | in-VPC DynamoDB latency-probe Lambda |
| `lambda_build_dir` | string | `../build/lambda` | assembled indexer package |
| `loadgen_build_dir` | string | `../build/loadgen` | assembled loadgen package |
| `enable_prod_web` | bool | `false` | ECR + ECS/ALB + Cognito hosted UI |
| `enable_frontend_cdn` | bool | `true` | host the SPA on S3+CloudFront |
| `enable_apigw` | bool | `true` | legacy API Gateway (off for ALB stack) |
| `enable_images_cdn` | bool | `false` | CloudFront in front of the image bucket |
| `cognito_domain_prefix` | string | `threadit-prod-auth` | Cognito hosted-UI domain prefix |
| `frontend_public_url` | string | `""` | origin for Cognito callback + CORS |

### Environment profiles (`terraform/envs/*.tfvars`)

| Profile | prod_web | search | dax | elasticache | frontend_cdn | images_cdn | apigw |
|---|---|---|---|---|---|---|---|
| `dev.tfvars` (Floci) | – | ✓ | ✗ | ✓ | – | ✗ | – |
| `awsbackend.tfvars` | ✓ | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `awsverify.tfvars` | ✓ | ✓ | ✗¹ | ✗¹ | ✗ | ✗ | ✗ |
| `prodweb.tfvars` | ✓ | ✓ | – | – | ✓ | ✓ | ✗ |

¹ DAX is account-blocked (SubscriptionRequiredException, like CloudFront) on the test
account; ElastiCache is wired + unit-tested, left off to bound cost. Flip on for a scale pass.

---

## 3. Module dependency diagram

```
                              ┌───────────┐
                              │  network  │  VPC, 2 public + 2 private subnets,
                              │  (always) │  IGW, DynamoDB gateway endpoint, SGs
                              └─────┬─────┘
          ┌─────────────┬──────────┼───────────┬──────────────┬─────────────┐
          ▼             ▼          ▼           ▼              ▼             ▼
   ┌───────────┐ ┌───────────┐ ┌───────┐ ┌───────────┐ ┌───────────┐ ┌──────────┐
   │ dynamodb  │ │  cognito  │ │  iam  │ │ s3_images │ │   dax     │ │elasticache│
   │ (always)  │ │ (always)  │ │(always)│ │ (always) │ │(enable_dax)│ │(enable_ec)│
   └─────┬─────┘ └─────┬─────┘ └───┬───┘ └─────┬─────┘ └─────┬─────┘ └────┬─────┘
         │ table_arn   │ issuer    │ roles     │ bucket      │ endpoint    │ endpoint
         │ stream_arn  │ client    │           │ oac         │ arn         │
         ▼             ▼           ▼           ▼             ▼             ▼
   ┌──────────────────────────────────────────────────────────────────────────┐
   │                         ecs_alb  (enable_prod_web)                         │
   │   ALB (public) → read/write Fargate tasks; injects every THREADIT_* env    │
   └──────────────────────────────────────────────────────────────────────────┘
         ▲                                   ▲                    ▲
         │ service_image                     │                    │
   ┌───────────┐                   ┌───────────────┐      ┌──────────────┐
   │   ecr     │                   │   indexer     │      │  cloudfront  │
   │(prod_web) │                   │ (enable_search)│      │(images_cdn)  │
   └───────────┘                   │ Streams→λ→OS   │      └──────────────┘
                                   │  + SQS DLQ     │
   ┌───────────┐  ┌───────────┐    └──────┬────────┘   ┌──────────┐  ┌─────────┐
   │ frontend  │  │ opensearch│◄──────────┘            │   waf    │  │ loadgen │
   │(front_cdn)│  │(enable_srch)                        │ (always) │  │(enable_lg)
   └───────────┘  └───────────┘                         └──────────┘  └─────────┘
```

Always-created: `network`, `dynamodb`, `cognito`, `iam`, `s3_images`, `waf`.
Everything else is flag-gated via `count`.

---

## 4. Module-by-module parameters

### 4.1 `network` — VPC foundation
Inputs: `name_prefix`, `cidr` (default `10.0.0.0/16`).
| Resource | Key parameters |
|---|---|
| `aws_vpc.main` | `cidr_block=10.0.0.0/16`, DNS support + hostnames on |
| `aws_subnet.private[2]` | `cidrsubnet(cidr,8,idx)` → `10.0.0.0/24`, `10.0.1.0/24`; one per AZ |
| `aws_subnet.public[2]` | `cidrsubnet(cidr,8,idx+10)` → `10.0.10.0/24`, `10.0.11.0/24`; `map_public_ip_on_launch=true` |
| `aws_internet_gateway.igw` | public egress (no NAT, cost control) |
| `aws_route_table.public` | `0.0.0.0/0 → igw` |
| `aws_vpc_endpoint.dynamodb` | Gateway endpoint on the private route table (DynamoDB stays off the internet) |
| `aws_security_group.alb` | ingress tcp/80 from `0.0.0.0/0` |
| `aws_security_group.service` | ingress tcp/8080–8081 from the ALB SG only |
| `aws_security_group.lambda` | egress-only (in-VPC Lambdas reach DynamoDB via the gateway endpoint) |
Outputs: `vpc_id`, `private_subnet_ids`, `public_subnet_ids`, `alb_security_group_id`, `service_security_group_id`, `lambda_security_group_id`.

### 4.2 `dynamodb` — single-table store
Inputs: `table_name`, `billing_mode` (`PAY_PER_REQUEST`), `enable_pitr` (`true`; forced off on Floci).
| Parameter | Value / meaning |
|---|---|
| `hash_key` / `range_key` | `PK` / `SK` (single-table composite key) |
| `GSI1` | `GSI1PK`/`GSI1SK`, `projection=INCLUDE` (postId,title,body,userId,createdAt,updatedAt,schemaVersion,attachment) — latest-posts via hourly buckets |
| `GSI2` | `GSI2PK`/`GSI2SK`, same projection — posts/comments by user |
| `stream_enabled` | `true`, `stream_view_type=NEW_AND_OLD_IMAGES` (search indexer source) |
| `ttl` | attribute `ttl`, enabled — expires idempotency sentinels |
| `server_side_encryption` | enabled |
| `point_in_time_recovery` | `var.enable_pitr` |
Outputs: `table_name`, `table_arn`, `stream_arn`.

### 4.3 `cognito` — auth
Inputs: `pool_name`, `domain_prefix`, `callback_url`, `logout_url`.
| Parameter | Value |
|---|---|
| user pool | `username_attributes=["email"]`, `auto_verified=["email"]` |
| password policy | min 8, upper+lower+number required, symbols optional |
| `allow_admin_create_user_only` | `false` (self-service sign-up) |
| verification | `CONFIRM_WITH_CODE` (email code) |
| app client | `generate_secret=false` (public SPA client) |
| OAuth | flows `["code"]`, scopes `["openid","email","profile"]`, IdP `["COGNITO"]` |
| auth flows | `ALLOW_USER_SRP_AUTH`, `ALLOW_REFRESH_TOKEN_AUTH` |
| `prevent_user_existence_errors` | `ENABLED` |
Outputs: `user_pool_id`, `app_client_id`, `issuer` (JWKS issuer URL), `hosted_domain`.

### 4.4 `iam` — least-privilege task roles
Inputs: `name_prefix`, `table_arn`, `images_bucket_arn`, `enable_images`, `dax_cluster_arn`, `enable_dax`.
| Role | Policy |
|---|---|
| `post-write` | `dynamodb:PutItem,UpdateItem,GetItem,Query` (Get/Query for idempotency + parent lookup; no Delete) + `s3:PutObject` on images (if `enable_images`) |
| `post-read` | `dynamodb:GetItem,Query` + `s3:GetObject` on images (presigned GET is signed with the role) + `dax:GetItem,Query,BatchGetItem,Scan` (if `enable_dax`) |
| `exec` | managed `AmazonECSTaskExecutionRolePolicy` (pull image, write logs) |
Assume principal: `ecs-tasks.amazonaws.com`.
Outputs: `write_role_arn`, `read_role_arn`, `execution_role_arn`.

### 4.5 `s3_images` — post images
Inputs: `name_prefix`, `enable_cloudfront`, `cors_origin`.
| Parameter | Value |
|---|---|
| bucket | `${name_prefix}-images` |
| public access block | all four blocks `true` (fully private) |
| encryption | SSE-KMS (`aws:kms`) |
| versioning | Enabled |
| CORS rule | methods `PUT,GET`, origin `cors_origin`, expose `ETag`, max-age 600 (only if `cors_origin` set) |
| OAC | `sigv4` "always" signing (only if `enable_cloudfront`) |
Outputs: `bucket_name`, `bucket_arn`, `bucket_regional_domain`, `oac_id`.

### 4.6 `ecr` — image registry (`enable_prod_web`)
`${name_prefix}-service`, `image_tag_mutability=MUTABLE`, `force_delete=true`, `scan_on_push=true`.

### 4.7 `ecs_alb` — compute + entry (`enable_prod_web`)
Inputs: `image`, `region`, `table_name`, `subnet_ids`, `alb_sg_id`, `service_sg_id`, `vpc_id`, `write_role_arn`, `read_role_arn`, `execution_role_arn`, `cognito_issuer`, `cognito_audience`, `cors_origin`, `attachments_bucket`, `images_cloudfront_domain`, `opensearch_endpoint`, `dax_endpoint`, `redis_endpoint`.
| Resource | Key parameters |
|---|---|
| `aws_ecs_cluster.main` | `${name_prefix}-cluster` |
| log group | `/ecs/${name_prefix}`, retention 7 days |
| task defs (read, write) | Fargate, `awsvpc`, cpu `256`, memory `512`, task role per service |
| container env | `APP_MODULE`, `PORT`, `THREADIT_TABLE_NAME`, `_AWS_REGION`, `_CORS_ALLOW_ORIGINS`, `_COGNITO_ISSUER`, `_COGNITO_AUDIENCE`, `_ATTACHMENTS_BUCKET`, `_IMAGES_CLOUDFRONT_DOMAIN`, `_OPENSEARCH_ENDPOINT`, `_OPENSEARCH_SIGN`, `_DAX_ENDPOINT` (read only), `_REDIS_ENDPOINT` |
| `aws_lb.api` | internet-facing ALB in the ALB SG + public subnets |
| target groups | read `:8080`, write `:8081`, `target_type=ip`, health `/healthz` (2 healthy / 3 unhealthy, 15s interval) |
| listener | port 80; default → read TG |
| listener rule (prio 10) | methods `POST,PUT,DELETE,PATCH` → write TG |
| services | `desired_count=1`, Fargate, `assign_public_ip=true`, in the service SG |
Output: `alb_dns`.

### 4.8 `opensearch` — search (`enable_search`)
Inputs: `name_prefix`, `instance_count` (1), `engine_version` (`OpenSearch_2.11`), `access_role_arns`.
| Parameter | Value |
|---|---|
| cluster | `t3.small.search` × `instance_count` |
| EBS | enabled, 10 GiB |
| encryption | at-rest + node-to-node on; `enforce_https=true` |
| domain policy | `es:ESHttp*` allowed for `access_role_arns` (indexer + read role) |
Outputs: `endpoint` (https), `arn`.

### 4.9 `indexer` — Streams→OpenSearch (`enable_search`)
Inputs: `stream_arn`, `opensearch_endpoint`, `source_dir`, `opensearch_sign` (true on AWS), `region`.
| Resource | Key parameters |
|---|---|
| Lambda | `python3.12`, handler `services.indexer.handler.handler`, timeout 30s; env `THREADIT_OPENSEARCH_ENDPOINT/_SIGN/_AWS_REGION` |
| role | DynamoDB Streams read (`GetRecords`,`GetShardIterator`,`DescribeStream`,`ListStreams`) + `sqs:SendMessage` + logs |
| event source mapping | on the table stream, `starting_position=LATEST`, `batch_size=100`, `maximum_retry_attempts=3`, `on_failure → SQS DLQ` |
| `aws_sqs_queue.dlq` | `${name_prefix}-indexer-dlq` |
Outputs: `function_name`, `dlq_url`.

### 4.10 `dax` — DynamoDB read cache (`enable_dax`)
Inputs: `subnet_ids`, `table_arn`, `vpc_id`, `client_sg_id`, `create_sg`.
| Parameter | Value |
|---|---|
| cluster | `dax.t3.small`, `replication_factor=1` |
| role | assumes `dax.amazonaws.com`; `dynamodb:GetItem,Query,BatchGetItem` |
| SG (if `create_sg`) | ingress tcp/8111 from `client_sg_id` (the read service) |
Outputs: `cluster_endpoint`, `cluster_arn`.
> Note: blocked by AWS account verification on the current account (SubscriptionRequiredException).

### 4.11 `elasticache` — Redis rate-limit state (`enable_elasticache`)
Inputs: `subnet_ids`, `vpc_id`, `client_sg_id`, `create_sg`.
| Parameter | Value |
|---|---|
| cluster | engine `redis`, `cache.t3.micro`, `num_cache_nodes=1` |
| SG (if `create_sg`) | ingress tcp/6379 from `client_sg_id` (the services) |
Output: `endpoint`.

### 4.12 `cloudfront` — image CDN (`enable_images_cdn`)
Inputs: `images_bucket_regional_domain`, `oac_id`.
Origin = S3 via OAC; `viewer_protocol_policy=redirect-to-https`; methods `GET,HEAD`;
Managed-CachingOptimized cache policy; `price_class=PriceClass_100`; default cert.
Output: `domain_name`.
> Note: blocked by AWS account verification on the current account.

### 4.13 `waf` — volumetric limiter (always)
Regional WAFv2 ACL, default `allow`, one rate-based rule `limit=2000` per IP (`block`).
> Note: WAFv2 cannot associate to an HTTP API (finding F10); enforcement is edge/staging-verified.
Output: `web_acl_arn`.

### 4.14 `loadgen` — in-VPC latency probe (`enable_loadgen`)
Lambda `python3.12`, handler `services.loadgen.handler.handler`, timeout 120s, in private
subnets + lambda SG; role has `dynamodb:GetItem,Query` + `AWSLambdaVPCAccessExecutionRole`.
Output: `function_name`. (Produced the real in-region p99 numbers in `NFR_REPORT.md`.)

### 4.15 `apigw` / `ecs` (legacy, gated off)
`apigw` builds an HTTP API with a Cognito JWT authorizer + stage throttling
(rate 2000 / burst 1000); `ecs` is the pre-ALB service module. Both superseded by
`ecs_alb` and off in current profiles; retained for reference.

---

## 5. Root outputs (`terraform/outputs.tf`)

`table_name`, `stream_arn`, `cognito_user_pool_id`, `cognito_app_client_id`,
`cognito_hosted_domain`, `api_endpoint` (apigw, when enabled), `write_role_arn`,
`read_role_arn`, `images_bucket`, `alb_dns`, `ecr_repository_url`, plus the
frontend CloudFront URL/bucket/distribution when `enable_frontend_cdn`.

---

## 6. How to apply

```bash
# dev (Floci): make tf-apply ENV=dev   (or `make app-floci` which wraps it)
# prod backend (no CloudFront):
make aws-up        # builds+pushes image, terraform apply envs/awsbackend.tfvars
make aws-down      # terraform destroy
```

All applies are parameterized only by the chosen `envs/*.tfvars` + `service_image`;
the modules themselves never change between environments.
