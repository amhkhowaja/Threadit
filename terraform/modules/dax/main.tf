variable "name_prefix" { type = string }
variable "subnet_ids" { type = list(string) }
variable "table_arn" { type = string }

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["dax.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "ddb" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:BatchGetItem"]
    resources = [var.table_arn, "${var.table_arn}/index/*"]
  }
}

resource "aws_iam_role" "dax" {
  name               = "${var.name_prefix}-dax"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy" "dax" {
  name   = "dax-ddb"
  role   = aws_iam_role.dax.id
  policy = data.aws_iam_policy_document.ddb.json
}

resource "aws_dax_subnet_group" "dax" {
  name       = "${var.name_prefix}-dax"
  subnet_ids = var.subnet_ids
}

resource "aws_dax_cluster" "read_cache" {
  cluster_name       = "${var.name_prefix}-dax"
  iam_role_arn       = aws_iam_role.dax.arn
  node_type          = "dax.t3.small"
  replication_factor = 1
  subnet_group_name  = aws_dax_subnet_group.dax.name
}

output "cluster_endpoint" {
  value = aws_dax_cluster.read_cache.cluster_address
}
