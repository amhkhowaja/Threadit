terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Dev targets Floci (localhost:4566); prod targets real AWS. One codebase (FLOCI doc §4).
provider "aws" {
  region = var.region

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
      ecs            = var.floci_endpoint
      ec2            = var.floci_endpoint
    }
  }
}

module "dynamodb" {
  source       = "./modules/dynamodb"
  table_name   = var.table_name
  billing_mode = var.use_floci ? "PAY_PER_REQUEST" : var.ddb_billing_mode
  enable_pitr  = !var.use_floci # PITR acceptance on Floci is [VERIFY] (FLOCI doc)
}

module "cognito" {
  source    = "./modules/cognito"
  pool_name = "${var.name_prefix}-users"
}

module "iam" {
  source            = "./modules/iam"
  name_prefix       = var.name_prefix
  table_arn         = module.dynamodb.table_arn
  images_bucket_arn = module.s3_images.bucket_arn
}

module "s3_images" {
  source            = "./modules/s3_images"
  name_prefix       = var.name_prefix
  enable_cloudfront = var.enable_cloudfront
}

module "waf" {
  source      = "./modules/waf"
  name_prefix = var.name_prefix
}

module "apigw" {
  source           = "./modules/apigw"
  name_prefix      = var.name_prefix
  cognito_issuer   = module.cognito.issuer
  cognito_audience = module.cognito.app_client_id
}

# NOTE: WAFv2 cannot associate to API Gateway v2 (HTTP API). P1 volumetric limiting is
# API Gateway stage throttling (see apigw module). The WAF ACL is retained for the
# CloudFront front added in P2 (FLOCI/ADR-008).

module "network" {
  source      = "./modules/network"
  name_prefix = var.name_prefix
}

module "ecs" {
  count              = var.enable_ecs ? 1 : 0
  source             = "./modules/ecs"
  name_prefix        = var.name_prefix
  image              = var.service_image
  table_name         = module.dynamodb.table_name
  aws_endpoint_url   = var.use_floci ? var.floci_endpoint : ""
  region             = var.region
  write_role_arn     = module.iam.write_role_arn
  read_role_arn      = module.iam.read_role_arn
  execution_role_arn = module.iam.execution_role_arn
  subnet_ids         = module.network.private_subnet_ids
}
