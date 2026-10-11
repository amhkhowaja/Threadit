variable "name_prefix" { type = string }
variable "image" { type = string }
variable "table_name" { type = string }
variable "aws_endpoint_url" {
  type    = string
  default = ""
}
variable "write_role_arn" { type = string }
variable "read_role_arn" { type = string }
variable "execution_role_arn" { type = string }
variable "subnet_ids" { type = list(string) }
variable "region" { type = string }

resource "aws_ecs_cluster" "main" {
  name = "${var.name_prefix}-cluster"
}

locals {
  services = {
    write = { module = "services.post_write.app", port = 8080, role = var.write_role_arn }
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
        { name = "THREADIT_AWS_ENDPOINT_URL", value = var.aws_endpoint_url },
      ]
    }
  ])
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
    assign_public_ip = false
  }
}

output "cluster_arn" {
  value = aws_ecs_cluster.main.arn
}
