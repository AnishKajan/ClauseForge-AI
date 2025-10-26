# LexiScan Infrastructure - Variables
variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# Networking
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Database
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "lexiscan"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "lexiscan"
}

variable "backup_retention_period" {
  description = "Database backup retention period in days"
  type        = number
  default     = 7
}

variable "backup_window" {
  description = "Database backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Database maintenance window"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

# Redis
variable "redis_node_type" {
  description = "ElastiCache Redis node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_nodes" {
  description = "Number of Redis cache nodes"
  type        = number
  default     = 1
}

# S3
variable "enable_s3_versioning" {
  description = "Enable S3 bucket versioning"
  type        = bool
  default     = true
}

variable "s3_lifecycle_rules" {
  description = "S3 lifecycle rules"
  type = list(object({
    id     = string
    status = string
    expiration = object({
      days = number
    })
  }))
  default = [
    {
      id     = "delete_old_versions"
      status = "Enabled"
      expiration = {
        days = 90
      }
    }
  ]
}

# ECS Configuration
variable "backend_image_uri" {
  description = "Backend Docker image URI"
  type        = string
}

variable "frontend_image_uri" {
  description = "Frontend Docker image URI"
  type        = string
}

variable "backend_cpu" {
  description = "Backend task CPU units"
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Backend task memory in MB"
  type        = number
  default     = 1024
}

variable "frontend_cpu" {
  description = "Frontend task CPU units"
  type        = number
  default     = 256
}

variable "frontend_memory" {
  description = "Frontend task memory in MB"
  type        = number
  default     = 512
}

variable "backend_desired_count" {
  description = "Desired number of backend tasks"
  type        = number
  default     = 2
}

variable "frontend_desired_count" {
  description = "Desired number of frontend tasks"
  type        = number
  default     = 2
}

# Environment Variables
variable "environment_variables" {
  description = "Environment variables for the application"
  type        = map(string)
  default     = {}
}

# Secrets
variable "jwt_secret" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "stripe_secret_key" {
  description = "Stripe secret key"
  type        = string
  sensitive   = true
  default     = ""
}

# Monitoring
variable "alert_email" {
  description = "Email address for CloudWatch alerts"
  type        = string
}

# DNS
variable "domain_name" {
  description = "Domain name for the application (optional)"
  type        = string
  default     = ""
}