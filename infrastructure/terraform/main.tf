# LexiScan Infrastructure - Main Configuration
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    # Backend configuration will be provided via backend config file
    # terraform init -backend-config=backend-config/staging.hcl
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "lexiscan"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Local values
locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  
  common_tags = {
    Project     = "lexiscan"
    Environment = var.environment
    ManagedBy   = "terraform"
  }
  
  # Naming convention
  name_prefix = "lexiscan-${var.environment}"
}

# VPC and Networking
module "vpc" {
  source = "./modules/vpc"
  
  name_prefix         = local.name_prefix
  vpc_cidr           = var.vpc_cidr
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)
  
  tags = local.common_tags
}

# Security Groups
module "security_groups" {
  source = "./modules/security"
  
  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  
  tags = local.common_tags
}

# RDS Database
module "database" {
  source = "./modules/database"
  
  name_prefix           = local.name_prefix
  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  security_group_ids   = [module.security_groups.database_sg_id]
  
  db_instance_class    = var.db_instance_class
  db_allocated_storage = var.db_allocated_storage
  db_name             = var.db_name
  db_username         = var.db_username
  
  backup_retention_period = var.backup_retention_period
  backup_window          = var.backup_window
  maintenance_window     = var.maintenance_window
  
  tags = local.common_tags
}

# ElastiCache Redis
module "redis" {
  source = "./modules/redis"
  
  name_prefix        = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_ids = [module.security_groups.redis_sg_id]
  
  node_type         = var.redis_node_type
  num_cache_nodes   = var.redis_num_nodes
  
  tags = local.common_tags
}

# S3 Buckets
module "storage" {
  source = "./modules/storage"
  
  name_prefix = local.name_prefix
  
  enable_versioning = var.enable_s3_versioning
  lifecycle_rules   = var.s3_lifecycle_rules
  
  tags = local.common_tags
}

# SQS Queues
module "queues" {
  source = "./modules/queues"
  
  name_prefix = local.name_prefix
  
  tags = local.common_tags
}

# ECS Cluster and Services
module "ecs" {
  source = "./modules/ecs"
  
  name_prefix        = local.name_prefix
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  private_subnet_ids = module.vpc.private_subnet_ids
  
  # Security groups
  alb_security_group_id     = module.security_groups.alb_sg_id
  backend_security_group_id = module.security_groups.backend_sg_id
  frontend_security_group_id = module.security_groups.frontend_sg_id
  
  # Database connection
  database_endpoint = module.database.endpoint
  database_name     = var.db_name
  database_username = var.db_username
  database_password = module.database.password
  
  # Redis connection
  redis_endpoint = module.redis.endpoint
  
  # S3 bucket
  documents_bucket = module.storage.documents_bucket_name
  
  # SQS queues
  processing_queue_url = module.queues.processing_queue_url
  
  # Application configuration
  backend_image_uri  = var.backend_image_uri
  frontend_image_uri = var.frontend_image_uri
  
  backend_cpu    = var.backend_cpu
  backend_memory = var.backend_memory
  frontend_cpu   = var.frontend_cpu
  frontend_memory = var.frontend_memory
  
  backend_desired_count  = var.backend_desired_count
  frontend_desired_count = var.frontend_desired_count
  
  # Environment variables
  environment_variables = var.environment_variables
  
  tags = local.common_tags
}

# CloudWatch Monitoring
module "monitoring" {
  source = "./modules/monitoring"
  
  name_prefix = local.name_prefix
  
  # ECS cluster
  ecs_cluster_name = module.ecs.cluster_name
  ecs_service_names = [
    module.ecs.backend_service_name,
    module.ecs.frontend_service_name
  ]
  
  # Database
  db_instance_id = module.database.instance_id
  
  # Redis
  redis_cluster_id = module.redis.cluster_id
  
  # Load balancer
  alb_arn = module.ecs.alb_arn
  
  # SNS topic for alerts
  alert_email = var.alert_email
  
  tags = local.common_tags
}

# Secrets Manager
module "secrets" {
  source = "./modules/secrets"
  
  name_prefix = local.name_prefix
  
  secrets = {
    database_password = module.database.password
    jwt_secret       = var.jwt_secret
    anthropic_api_key = var.anthropic_api_key
    openai_api_key   = var.openai_api_key
    stripe_secret_key = var.stripe_secret_key
  }
  
  tags = local.common_tags
}

# Lambda Functions
module "lambda" {
  source = "./modules/lambda"
  
  name_prefix = local.name_prefix
  vpc_id      = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  
  # Security groups
  lambda_security_group_id = module.security_groups.lambda_sg_id
  
  # S3 bucket for virus scanning
  documents_bucket = module.storage.documents_bucket_name
  
  tags = local.common_tags
}

# WAF for Application Load Balancer
module "waf" {
  source = "./modules/waf"
  
  name_prefix = local.name_prefix
  alb_arn     = module.ecs.alb_arn
  
  tags = local.common_tags
}

# Route53 and SSL Certificate (if domain is provided)
module "dns" {
  source = "./modules/dns"
  count  = var.domain_name != "" ? 1 : 0
  
  name_prefix   = local.name_prefix
  domain_name   = var.domain_name
  alb_dns_name  = module.ecs.alb_dns_name
  alb_zone_id   = module.ecs.alb_zone_id
  
  tags = local.common_tags
}