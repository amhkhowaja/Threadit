variable "name_prefix" { type = string }
variable "subnet_ids" { type = list(string) }
variable "vpc_id" {
  type    = string
  default = ""
}
variable "client_sg_id" {
  type    = string
  default = ""
}
variable "create_sg" {
  type    = bool
  default = false
}

resource "aws_elasticache_subnet_group" "cache" {
  name       = "${var.name_prefix}-cache"
  subnet_ids = var.subnet_ids
}

# Allow the services (client SG) to reach Redis on 6379.
resource "aws_security_group" "cache" {
  count       = var.create_sg ? 1 : 0
  name        = "${var.name_prefix}-cache-sg"
  description = "ElastiCache Redis access from the services"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 6379
    to_port         = 6379
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

resource "aws_elasticache_cluster" "cache" {
  cluster_id         = "${var.name_prefix}-cache"
  engine             = "redis"
  node_type          = "cache.t3.micro"
  num_cache_nodes    = 1
  subnet_group_name  = aws_elasticache_subnet_group.cache.name
  security_group_ids = var.create_sg ? [aws_security_group.cache[0].id] : null
}

output "endpoint" {
  value = aws_elasticache_cluster.cache.cache_nodes[0].address
}
