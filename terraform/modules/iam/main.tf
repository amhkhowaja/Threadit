variable "name_prefix" { type = string }
variable "table_arn" { type = string }
variable "images_bucket_arn" {
  type    = string
  default = ""
}
variable "enable_images" {
  type    = bool
  default = true
}
variable "dax_cluster_arn" {
  type    = string
  default = ""
}
variable "enable_dax" {
  type    = bool
  default = false
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Write role: Put/Update + the reads the write path legitimately needs
# (idempotency sentinel resolution, parent-comment lookup). Still no delete. (R9)
data "aws_iam_policy_document" "write" {
  statement {
    actions = [
      "dynamodb:PutItem",
      "dynamodb:UpdateItem",
      "dynamodb:GetItem",
      "dynamodb:Query",
    ]
    resources = [var.table_arn, "${var.table_arn}/index/*"]
  }
}

# Read role: only Get/Query (never writes).
data "aws_iam_policy_document" "read" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:Query"]
    resources = [var.table_arn, "${var.table_arn}/index/*"]
  }
}

resource "aws_iam_role" "write" {
  name               = "${var.name_prefix}-post-write"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role" "read" {
  name               = "${var.name_prefix}-post-read"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "write" {
  name   = "ddb-write"
  role   = aws_iam_role.write.id
  policy = data.aws_iam_policy_document.write.json
}

# S3 image upload (presign) — only PutObject on the image bucket (least privilege).
data "aws_iam_policy_document" "write_s3" {
  count = var.enable_images ? 1 : 0
  statement {
    actions   = ["s3:PutObject"]
    resources = ["${var.images_bucket_arn}/*"]
  }
}

resource "aws_iam_role_policy" "write_s3" {
  count  = var.enable_images ? 1 : 0
  name   = "s3-images-write"
  role   = aws_iam_role.write.id
  policy = data.aws_iam_policy_document.write_s3[0].json
}

resource "aws_iam_role_policy" "read" {
  name   = "ddb-read"
  role   = aws_iam_role.read.id
  policy = data.aws_iam_policy_document.read.json
}

# S3 image read (presigned GET is signed with the read role's creds, so the role
# itself must be allowed s3:GetObject on the image objects). (least privilege)
data "aws_iam_policy_document" "read_s3" {
  count = var.enable_images ? 1 : 0
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${var.images_bucket_arn}/*"]
  }
}

resource "aws_iam_role_policy" "read_s3" {
  count  = var.enable_images ? 1 : 0
  name   = "s3-images-read"
  role   = aws_iam_role.read.id
  policy = data.aws_iam_policy_document.read_s3[0].json
}

# DAX data-plane reads (only when a DAX cluster is provisioned). DAX passes
# ConsistentRead through to DynamoDB, which the read role already allows.
data "aws_iam_policy_document" "read_dax" {
  count = var.enable_dax ? 1 : 0
  statement {
    actions = [
      "dax:GetItem",
      "dax:Query",
      "dax:BatchGetItem",
      "dax:Scan",
    ]
    resources = [var.dax_cluster_arn]
  }
}

resource "aws_iam_role_policy" "read_dax" {
  count  = var.enable_dax ? 1 : 0
  name   = "dax-read"
  role   = aws_iam_role.read.id
  policy = data.aws_iam_policy_document.read_dax[0].json
}

# ECS task execution role (pull image, write logs).
resource "aws_iam_role" "execution" {
  name               = "${var.name_prefix}-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

output "write_role_arn" {
  value = aws_iam_role.write.arn
}
output "read_role_arn" {
  value = aws_iam_role.read.arn
}
output "execution_role_arn" {
  value = aws_iam_role.execution.arn
}
