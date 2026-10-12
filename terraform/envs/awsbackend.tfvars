use_floci        = false
region           = "eu-central-1"
name_prefix      = "threadit-prod"
table_name       = "threadit"
ddb_billing_mode = "PAY_PER_REQUEST"

enable_prod_web     = true
enable_frontend_cdn = false # frontend runs locally; no CloudFront (account-verification blocked)
enable_images_cdn   = false # images served via presigned S3 GET
enable_apigw        = false
enable_ecs          = false
enable_search       = true
enable_elasticache  = false
enable_dax          = false
enable_cloudfront   = false
enable_xray         = false
enable_loadgen      = false

# Local frontend origin for Cognito callback + CORS.
frontend_public_url   = "http://localhost:5173"
cognito_domain_prefix = "threadit-prod-auth-ak"
service_image         = "PLACEHOLDER_SET_BY_DEPLOY"
