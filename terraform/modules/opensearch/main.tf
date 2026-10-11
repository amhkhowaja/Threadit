variable "name_prefix" { type = string }
variable "instance_count" {
  type    = number
  default = 1
}
variable "engine_version" {
  type    = string
  default = "OpenSearch_2.11"
}

resource "aws_opensearch_domain" "search" {
  domain_name    = "${var.name_prefix}-search"
  engine_version = var.engine_version

  cluster_config {
    instance_type  = "t3.small.search"
    instance_count = var.instance_count
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https = true
  }
}

output "endpoint" {
  value = "https://${aws_opensearch_domain.search.endpoint}"
}
output "arn" {
  value = aws_opensearch_domain.search.arn
}
