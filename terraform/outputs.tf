output "table_name" {
  value = module.dynamodb.table_name
}
output "stream_arn" {
  value = module.dynamodb.stream_arn
}
output "cognito_user_pool_id" {
  value = module.cognito.user_pool_id
}
output "cognito_app_client_id" {
  value = module.cognito.app_client_id
}
output "api_endpoint" {
  value = var.enable_apigw ? module.apigw[0].api_endpoint : null
}
output "write_role_arn" {
  value = module.iam.write_role_arn
}
output "read_role_arn" {
  value = module.iam.read_role_arn
}
output "images_bucket" {
  value = module.s3_images.bucket_name
}

output "frontend_url" {
  value = var.enable_prod_web && var.enable_frontend_cdn ? module.frontend[0].url : null
}
output "frontend_bucket" {
  value = var.enable_prod_web && var.enable_frontend_cdn ? module.frontend[0].bucket : null
}
output "frontend_distribution_id" {
  value = var.enable_prod_web && var.enable_frontend_cdn ? module.frontend[0].distribution_id : null
}
output "alb_dns" {
  value = var.enable_prod_web ? module.ecs_alb[0].alb_dns : null
}
output "ecr_repository_url" {
  value = var.enable_prod_web ? module.ecr[0].repository_url : null
}
output "cognito_hosted_domain" {
  value = module.cognito.hosted_domain
}
