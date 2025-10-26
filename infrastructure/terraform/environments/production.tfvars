# Production environment configuration
environment = "production"
aws_region  = "us-east-1"

# Networking
vpc_cidr = "10.1.0.0/16"

# Database
db_instance_class    = "db.t3.small"
db_allocated_storage = 100
backup_retention_period = 7

# Redis
redis_node_type = "cache.t3.small"
redis_num_nodes = 2

# ECS Configuration
backend_cpu    = 512
backend_memory = 1024
frontend_cpu   = 256
frontend_memory = 512

backend_desired_count  = 2
frontend_desired_count = 2

# S3 Configuration
enable_s3_versioning = true

# Environment Variables
environment_variables = {
  ENVIRONMENT = "production"
  DEBUG       = "false"
  LOG_LEVEL   = "INFO"
}