# Staging environment configuration
environment = "staging"
aws_region  = "us-east-1"

# Networking
vpc_cidr = "10.0.0.0/16"

# Database
db_instance_class    = "db.t3.micro"
db_allocated_storage = 20
backup_retention_period = 3

# Redis
redis_node_type = "cache.t3.micro"
redis_num_nodes = 1

# ECS Configuration
backend_cpu    = 256
backend_memory = 512
frontend_cpu   = 256
frontend_memory = 512

backend_desired_count  = 1
frontend_desired_count = 1

# Environment Variables
environment_variables = {
  ENVIRONMENT = "staging"
  DEBUG       = "false"
  LOG_LEVEL   = "INFO"
}