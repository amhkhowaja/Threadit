variable "pool_name" { type = string }
variable "domain_prefix" { type = string }
variable "callback_url" {
  type    = string
  default = "http://localhost:5173/auth/callback"
}
variable "logout_url" {
  type    = string
  default = "http://localhost:5173"
}

resource "aws_cognito_user_pool" "users" {
  name                     = var.pool_name
  auto_verified_attributes = ["email"]
  username_attributes      = ["email"]

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = false
  }

  admin_create_user_config {
    allow_admin_create_user_only = false # self-service sign-up
  }

  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
  }
}

resource "aws_cognito_user_pool_domain" "domain" {
  domain       = var.domain_prefix
  user_pool_id = aws_cognito_user_pool.users.id
}

resource "aws_cognito_user_pool_client" "app" {
  name                                 = "${var.pool_name}-app"
  user_pool_id                         = aws_cognito_user_pool.users.id
  generate_secret                      = false
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors        = "ENABLED"
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]
  callback_urls                        = [var.callback_url]
  logout_urls                          = [var.logout_url]
}

data "aws_region" "current" {}

output "user_pool_id" {
  value = aws_cognito_user_pool.users.id
}
output "app_client_id" {
  value = aws_cognito_user_pool_client.app.id
}
output "issuer" {
  value = "https://cognito-idp.${data.aws_region.current.region}.amazonaws.com/${aws_cognito_user_pool.users.id}"
}
output "hosted_domain" {
  value = "https://${var.domain_prefix}.auth.${data.aws_region.current.region}.amazoncognito.com"
}
