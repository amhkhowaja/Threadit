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
  value = module.apigw.api_endpoint
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
