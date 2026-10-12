variable "name_prefix" { type = string }
variable "enable_cloudfront" {
  type    = bool
  default = true
}
variable "cors_origin" {
  type    = string
  default = ""
}

resource "aws_s3_bucket" "images" {
  bucket = "${var.name_prefix}-images"
}

# Allow the web origin to upload directly via presigned PUT (browser) and read.
resource "aws_s3_bucket_cors_configuration" "images" {
  count  = var.cors_origin == "" ? 0 : 1
  bucket = aws_s3_bucket.images.id
  cors_rule {
    allowed_methods = ["PUT", "GET"]
    allowed_origins = [var.cors_origin]
    allowed_headers = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 600
  }
}

resource "aws_s3_bucket_public_access_block" "images" {
  bucket                  = aws_s3_bucket.images.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "images" {
  bucket = aws_s3_bucket.images.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_versioning" "images" {
  bucket = aws_s3_bucket.images.id
  versioning_configuration {
    status = "Enabled"
  }
}

# CloudFront OAC delivery (prod); control-plane only on Floci (F2).
resource "aws_cloudfront_origin_access_control" "images" {
  count                             = var.enable_cloudfront ? 1 : 0
  name                              = "${var.name_prefix}-images-oac"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

output "bucket_name" {
  value = aws_s3_bucket.images.bucket
}
output "bucket_arn" {
  value = aws_s3_bucket.images.arn
}
output "bucket_regional_domain" {
  value = aws_s3_bucket.images.bucket_regional_domain_name
}
output "oac_id" {
  value = var.enable_cloudfront ? aws_cloudfront_origin_access_control.images[0].id : ""
}
