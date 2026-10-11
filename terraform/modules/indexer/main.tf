variable "name_prefix" { type = string }
variable "stream_arn" { type = string }
variable "opensearch_endpoint" { type = string }
variable "source_dir" { type = string }

data "archive_file" "indexer" {
  type        = "zip"
  output_path = "${path.module}/.build/indexer.zip"
  source_dir  = var.source_dir
}

resource "aws_sqs_queue" "dlq" {
  name = "${var.name_prefix}-indexer-dlq"
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
    actions = [
      "dynamodb:GetRecords", "dynamodb:GetShardIterator",
      "dynamodb:DescribeStream", "dynamodb:ListStreams",
    ]
    resources = [var.stream_arn, "${var.stream_arn}/*"]
  }
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.dlq.arn]
  }
  statement {
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["*"]
  }
}

resource "aws_iam_role" "indexer" {
  name               = "${var.name_prefix}-indexer"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy" "indexer" {
  name   = "indexer"
  role   = aws_iam_role.indexer.id
  policy = data.aws_iam_policy_document.perms.json
}

resource "aws_lambda_function" "indexer" {
  function_name    = "${var.name_prefix}-indexer"
  role             = aws_iam_role.indexer.arn
  handler          = "services.indexer.handler.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.indexer.output_path
  source_code_hash = data.archive_file.indexer.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      THREADIT_OPENSEARCH_ENDPOINT = var.opensearch_endpoint
    }
  }
}

resource "aws_lambda_event_source_mapping" "stream" {
  event_source_arn       = var.stream_arn
  function_name          = aws_lambda_function.indexer.arn
  starting_position      = "LATEST"
  batch_size             = 100
  maximum_retry_attempts = 3

  destination_config {
    on_failure {
      destination_arn = aws_sqs_queue.dlq.arn
    }
  }
}

output "function_name" {
  value = aws_lambda_function.indexer.function_name
}
output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}
