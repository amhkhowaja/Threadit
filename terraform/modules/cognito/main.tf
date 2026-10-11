variable "pool_name" { type = string }

resource "aws_cognito_user_pool" "users" {
  name = var.pool_name

  password_policy {
    minimum_length    = 12
    require_lowercase = true
    require_uppercase = true
    require_numbers   = true
    require_symbols   = true
  }

  admin_create_user_config {
    allow_admin_create_user_only = false
  }
}

resource "aws_cognito_user_pool_client" "app" {
  name                                 = "${var.pool_name}-app"
  user_pool_id                         = aws_cognito_user_pool.users.id
  generate_secret                      = false
  explicit_auth_flows                  = ["ALLOW_USER_SRP_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
  prevent_user_existence_errors        = "ENABLED"
  allowed_oauth_flows_user_pool_client = false
}

output "user_pool_id" {
  value = aws_cognito_user_pool.users.id
}
output "app_client_id" {
  value = aws_cognito_user_pool_client.app.id
}
output "issuer" {
  value = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.users.id}"
}

data "aws_region" "current" {}
