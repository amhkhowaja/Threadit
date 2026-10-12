variable "region" {
  type    = string
  default = "us-east-1"
}

variable "use_floci" {
  type        = bool
  default     = false
  description = "When true, target the local Floci emulator at floci_endpoint."
}

variable "floci_endpoint" {
  type    = string
  default = "http://localhost:4566"
}

variable "name_prefix" {
  type    = string
  default = "threadit-dev"
}

variable "table_name" {
  type    = string
  default = "threadit"
}

variable "ddb_billing_mode" {
  type    = string
  default = "PAY_PER_REQUEST"
}

# Capability toggles for Floci parity gaps (FLOCI doc §4.2).
variable "enable_dax" {
  type    = bool
  default = true
}

variable "enable_cloudfront" {
  type    = bool
  default = true
}

variable "enable_xray" {
  type    = bool
  default = true
}

variable "enable_ecs" {
  type        = bool
  default     = true
  description = "Provision ECS services (requires a built image)."
}

variable "service_image" {
  type    = string
  default = "threadit:local"
}

variable "enable_search" {
  type        = bool
  default     = true
  description = "Provision OpenSearch domain + Streams->Lambda indexer."
}

variable "enable_elasticache" {
  type        = bool
  default     = true
  description = "Provision ElastiCache (counters + rate-limit state)."
}

variable "lambda_build_dir" {
  type        = string
  default     = "../build/lambda"
  description = "Pre-assembled Lambda package dir (handler + threadit_core + deps)."
}

variable "enable_loadgen" {
  type        = bool
  default     = false
  description = "Provision the in-region DynamoDB latency-probe Lambda (perf testing)."
}

variable "loadgen_build_dir" {
  type    = string
  default = "../build/loadgen"
}

variable "enable_prod_web" {
  type        = bool
  default     = false
  description = "Full production web stack: ECR + ECS/ALB + Cognito hosted UI + frontend CloudFront."
}

variable "enable_frontend_cdn" {
  type        = bool
  default     = true
  description = "Host the frontend on S3+CloudFront. Off => frontend runs elsewhere (e.g. locally)."
}

variable "enable_apigw" {
  type        = bool
  default     = true
  description = "Legacy API Gateway module (off for the ALB-based prod web stack)."
}

variable "enable_images_cdn" {
  type        = bool
  default     = false
  description = "CloudFront distribution in front of the image bucket."
}

variable "cognito_domain_prefix" {
  type    = string
  default = "threadit-prod-auth"
}

variable "frontend_public_url" {
  type        = string
  default     = ""
  description = "Public origin for Cognito callback + CORS. If empty, uses the frontend CloudFront URL."
}
