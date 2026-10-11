variable "name_prefix" { type = string }
variable "cognito_issuer" { type = string }
variable "cognito_audience" { type = string }
variable "write_integration_uri" {
  type    = string
  default = "http://127.0.0.1:8081"
}
variable "read_integration_uri" {
  type    = string
  default = "http://127.0.0.1:8080"
}

resource "aws_apigatewayv2_api" "http" {
  name          = "${var.name_prefix}-api"
  protocol_type = "HTTP"
}

# Managed JWT verification (D6/I3): the authorizer validates Cognito tokens;
# services trust the gateway-injected `sub` claim.
resource "aws_apigatewayv2_authorizer" "cognito" {
  api_id           = aws_apigatewayv2_api.http.id
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  name             = "${var.name_prefix}-cognito"

  jwt_configuration {
    audience = [var.cognito_audience]
    issuer   = var.cognito_issuer
  }
}

resource "aws_apigatewayv2_integration" "write" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "HTTP_PROXY"
  integration_method     = "ANY"
  integration_uri        = var.write_integration_uri
  payload_format_version = "1.0"
}

resource "aws_apigatewayv2_integration" "read" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "HTTP_PROXY"
  integration_method     = "ANY"
  integration_uri        = var.read_integration_uri
  payload_format_version = "1.0"
}

locals {
  write_routes = ["POST /v1/posts", "POST /v1/posts/{post_id}/comments"]
  read_routes = [
    "GET /v1/posts",
    "GET /v1/posts/{post_id}",
    "GET /v1/posts/{post_id}/comments",
  ]
}

# Writes require the JWT authorizer; reads are public (FR6).
resource "aws_apigatewayv2_route" "write" {
  for_each           = toset(local.write_routes)
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = each.value
  target             = "integrations/${aws_apigatewayv2_integration.write.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.cognito.id
}

resource "aws_apigatewayv2_route" "read" {
  for_each           = toset(local.read_routes)
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = each.value
  target             = "integrations/${aws_apigatewayv2_integration.read.id}"
  authorization_type = "NONE"
}

resource "aws_apigatewayv2_stage" "v1" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true

  # Volumetric limiting for HTTP APIs is done via built-in stage throttling
  # (WAFv2 cannot associate to API Gateway v2 / HTTP APIs; that path needs CloudFront in P2).
  default_route_settings {
    throttling_rate_limit  = 2000
    throttling_burst_limit = 1000
  }
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.http.api_endpoint
}
output "api_arn" {
  value = aws_apigatewayv2_api.http.arn
}
