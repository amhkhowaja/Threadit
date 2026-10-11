variable "name_prefix" { type = string }
variable "table_arn" { type = string }
variable "table_name" { type = string }
variable "region" { type = string }
variable "source_dir" { type = string }
variable "subnet_ids" { type = list(string) }
variable "security_group_id" { type = string }

data "archive_file" "loadgen" {
  type        = "zip"
  output_path = "${path.module}/.build/loadgen.zip"
  source_dir  = var.source_dir
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "perms" {
  statement {
    actions   = ["dynamodb:GetItem", "dynamodb:Query"]
    resources = [var.table_arn, "${var.table_arn}/index/*"]
  }
  statement {
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
  }
}

resource "aws_iam_role" "loadgen" {
  name               = "${var.name_prefix}-loadgen"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy" "loadgen" {
  name   = "loadgen"
  role   = aws_iam_role.loadgen.id
  policy = data.aws_iam_policy_document.perms.json
}

resource "aws_iam_role_policy_attachment" "vpc_access" {
  role       = aws_iam_role.loadgen.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_lambda_function" "loadgen" {
  function_name    = "${var.name_prefix}-loadgen"
  role             = aws_iam_role.loadgen.arn
  handler          = "services.loadgen.handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.loadgen.output_path
  source_code_hash = data.archive_file.loadgen.output_base64sha256
  timeout          = 120

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [var.security_group_id]
  }

  environment {
    variables = {
      THREADIT_TABLE_NAME = var.table_name
      THREADIT_AWS_REGION = var.region
    }
  }
}

output "function_name" {
  value = aws_lambda_function.loadgen.function_name
}
