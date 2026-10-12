variable "name_prefix" { type = string }

resource "aws_ecr_repository" "service" {
  name                 = "${var.name_prefix}-service"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

output "repository_url" {
  value = aws_ecr_repository.service.repository_url
}
output "repository_name" {
  value = aws_ecr_repository.service.name
}
