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
  source      = "./modules/iam"
  name_prefix = var.name_prefix
  table_arn   = module.dynamodb.table_arn
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

resource "aws_wafv2_web_acl_association" "api" {
  resource_arn = module.apigw.api_arn
  web_acl_arn  = module.waf.web_acl_arn
}
