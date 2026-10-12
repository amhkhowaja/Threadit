variable "name_prefix" { type = string }
variable "subnet_ids" { type = list(string) }
variable "table_arn" { type = string }
variable "vpc_id" {
  type    = string
  default = ""
}
variable "client_sg_id" {
  type    = string
  default = ""
}

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

# Allow the read service (client SG) to reach DAX on 8111.
resource "aws_security_group" "dax" {
  count       = var.vpc_id == "" ? 0 : 1
  name        = "${var.name_prefix}-dax-sg"
  description = "DAX cluster access from the read service"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 8111
    to_port         = 8111
    protocol        = "tcp"
    security_groups = var.client_sg_id == "" ? null : [var.client_sg_id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_dax_cluster" "read_cache" {
  cluster_name       = "${var.name_prefix}-dax"
  iam_role_arn       = aws_iam_role.dax.arn
  node_type          = "dax.t3.small"
  replication_factor = 1
  subnet_group_name  = aws_dax_subnet_group.dax.name
  security_group_ids = var.vpc_id == "" ? null : [aws_security_group.dax[0].id]
}

output "cluster_endpoint" {
  value = aws_dax_cluster.read_cache.cluster_address
}

output "cluster_arn" {
  value = aws_dax_cluster.read_cache.arn
}
