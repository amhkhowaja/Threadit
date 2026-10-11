variable "table_name" { type = string }
variable "billing_mode" {
  type    = string
  default = "PAY_PER_REQUEST"
}
variable "enable_pitr" {
  type    = bool
  default = true
}

# Single-table design (SYSTEM_ARCHITECTURE §4 / PLANNING §1.6).
# Only key attributes are declared; all non-key attributes are schemaless.
resource "aws_dynamodb_table" "threadit" {
  name         = var.table_name
  billing_mode = var.billing_mode
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }
  attribute {
    name = "SK"
    type = "S"
  }
  attribute {
    name = "GSI1PK"
    type = "S"
  }
  attribute {
    name = "GSI1SK"
    type = "S"
  }
  attribute {
    name = "GSI2PK"
    type = "S"
  }
  attribute {
    name = "GSI2SK"
    type = "S"
  }

  # GSI1: latest posts via hourly time-buckets (AP3).
  global_secondary_index {
    name               = "GSI1"
    hash_key           = "GSI1PK"
    range_key          = "GSI1SK"
    projection_type    = "INCLUDE"
    non_key_attributes = ["title", "userId", "createdAt", "commentCountApprox"]
  }

  # GSI2: posts/comments by user (AP4).
  global_secondary_index {
    name               = "GSI2"
    hash_key           = "GSI2PK"
    range_key          = "GSI2SK"
    projection_type    = "INCLUDE"
    non_key_attributes = ["title", "userId", "createdAt"]
  }

  # Streams enabled in P1 (D1) — no consumer yet; P2/P3 attach without a table change.
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"

  # TTL drives idempotency sentinel expiry (I8).
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = var.enable_pitr
  }
}

output "table_name" {
  value = aws_dynamodb_table.threadit.name
}
output "table_arn" {
  value = aws_dynamodb_table.threadit.arn
}
output "stream_arn" {
  value = aws_dynamodb_table.threadit.stream_arn
}
