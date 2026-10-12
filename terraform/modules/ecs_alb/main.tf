variable "name_prefix" { type = string }
variable "image" { type = string }
variable "region" { type = string }
variable "table_name" { type = string }
variable "subnet_ids" { type = list(string) }
variable "alb_sg_id" { type = string }
variable "service_sg_id" { type = string }
variable "vpc_id" { type = string }
variable "write_role_arn" { type = string }
variable "read_role_arn" { type = string }
variable "execution_role_arn" { type = string }
variable "cognito_issuer" { type = string }
variable "cognito_audience" { type = string }
variable "cors_origin" { type = string }
variable "attachments_bucket" { type = string }
variable "images_cloudfront_domain" { type = string }
variable "opensearch_endpoint" {
  type    = string
  default = ""
}
variable "dax_endpoint" {
  type    = string
  default = ""
}

resource "aws_ecs_cluster" "main" {
  name = "${var.name_prefix}-cluster"
}

resource "aws_cloudwatch_log_group" "svc" {
  name              = "/ecs/${var.name_prefix}"
  retention_in_days = 7
}

locals {
  services = {
    write = { module = "services.post_write.app", port = 8081, role = var.write_role_arn }
    read  = { module = "services.post_read.app", port = 8080, role = var.read_role_arn }
  }
}

resource "aws_ecs_task_definition" "svc" {
  for_each                 = local.services
  family                   = "${var.name_prefix}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  task_role_arn            = each.value.role
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([
    {
      name         = each.key
      image        = var.image
      essential    = true
      portMappings = [{ containerPort = each.value.port }]
      environment = [
        { name = "APP_MODULE", value = each.value.module },
        { name = "PORT", value = tostring(each.value.port) },
        { name = "THREADIT_TABLE_NAME", value = var.table_name },
        { name = "THREADIT_AWS_REGION", value = var.region },
        { name = "THREADIT_CORS_ALLOW_ORIGINS", value = var.cors_origin },
        { name = "THREADIT_COGNITO_ISSUER", value = var.cognito_issuer },
        { name = "THREADIT_COGNITO_AUDIENCE", value = var.cognito_audience },
        { name = "THREADIT_ATTACHMENTS_BUCKET", value = var.attachments_bucket },
        { name = "THREADIT_IMAGES_CLOUDFRONT_DOMAIN", value = var.images_cloudfront_domain },
        { name = "THREADIT_OPENSEARCH_ENDPOINT", value = var.opensearch_endpoint },
        { name = "THREADIT_OPENSEARCH_SIGN", value = var.opensearch_endpoint == "" ? "false" : "true" },
        # DAX read cache: only the read service routes through it.
        { name = "THREADIT_DAX_ENDPOINT", value = each.key == "read" ? var.dax_endpoint : "" },
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.svc.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = each.key
        }
      }
    }
  ])
}

resource "aws_lb" "api" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_sg_id]
  subnets            = var.subnet_ids
}

resource "aws_lb_target_group" "svc" {
  for_each    = local.services
  name        = "${var.name_prefix}-${each.key}"
  port        = each.value.port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"
  health_check {
    path                = "/healthz"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
    timeout             = 5
  }
}

# Default -> read service; POST (writes) routed to the write service.
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.api.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.svc["read"].arn
  }
}

resource "aws_lb_listener_rule" "writes" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.svc["write"].arn
  }
  condition {
    http_request_method {
      values = ["POST", "PUT", "DELETE", "PATCH"]
    }
  }
}

resource "aws_ecs_service" "svc" {
  for_each        = local.services
  name            = "${var.name_prefix}-${each.key}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.svc[each.key].arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.service_sg_id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.svc[each.key].arn
    container_name   = each.key
    container_port   = each.value.port
  }

  depends_on = [aws_lb_listener.http]
}

output "alb_dns" {
  value = aws_lb.api.dns_name
}
