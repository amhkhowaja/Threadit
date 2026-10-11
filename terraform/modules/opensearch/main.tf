variable "name_prefix" { type = string }
variable "instance_count" {
  type    = number
  default = 1
}
variable "engine_version" {
  type    = string
  default = "OpenSearch_2.11"
}
variable "access_role_arns" {
  type    = list(string)
  default = []
}

data "aws_iam_policy_document" "access" {
  count = length(var.access_role_arns) > 0 ? 1 : 0
  statement {
    effect  = "Allow"
    actions = ["es:ESHttp*"]
    principals {
      type        = "AWS"
      identifiers = var.access_role_arns
    }
    resources = ["${aws_opensearch_domain.search.arn}/*"]
  }
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

resource "aws_opensearch_domain_policy" "access" {
  count           = length(var.access_role_arns) > 0 ? 1 : 0
  domain_name     = aws_opensearch_domain.search.domain_name
  access_policies = data.aws_iam_policy_document.access[0].json
}

output "endpoint" {
  value = "https://${aws_opensearch_domain.search.endpoint}"
}
output "arn" {
  value = aws_opensearch_domain.search.arn
}
