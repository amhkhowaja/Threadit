variable "name_prefix" { type = string }
variable "images_bucket_regional_domain" { type = string }
variable "oac_id" { type = string }

resource "aws_cloudfront_distribution" "images" {
  enabled = true
  comment = "${var.name_prefix}-images"

  origin {
    domain_name              = var.images_bucket_regional_domain
    origin_id                = "images-s3"
    origin_access_control_id = var.oac_id
  }

  default_cache_behavior {
    target_origin_id       = "images-s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    cache_policy_id        = "658327ea-f89d-4fab-a63d-7e88639e58f6" # Managed-CachingOptimized
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  price_class = "PriceClass_100"
}

output "domain_name" {
  value = aws_cloudfront_distribution.images.domain_name
}
