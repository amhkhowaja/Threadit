variable "name_prefix" { type = string }
variable "subnet_ids" { type = list(string) }

resource "aws_elasticache_subnet_group" "cache" {
  name       = "${var.name_prefix}-cache"
  subnet_ids = var.subnet_ids
}

resource "aws_elasticache_cluster" "cache" {
  cluster_id        = "${var.name_prefix}-cache"
  engine            = "redis"
  node_type         = "cache.t3.micro"
  num_cache_nodes   = 1
  subnet_group_name = aws_elasticache_subnet_group.cache.name
}

output "endpoint" {
  value = aws_elasticache_cluster.cache.cache_nodes[0].address
}
