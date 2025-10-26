# LexiScan Infrastructure - Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = module.vpc.vpc_id
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = module.vpc.private_subnet_ids
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = module.database.endpoint
  sensitive   = true
}

output "database_port" {
  description = "RDS instance port"
  value       = module.database.port
}

output "redis_endpoint" {
  description = "ElastiCache Redis endpoint"
  value       = module.redis.endpoint
}

output "redis_port" {
  description = "ElastiCache Redis port"
  value       = module.redis.port
}

output "documents_bucket_name" {
  description = "S3 bucket name for documents"
  value       = module.storage.documents_bucket_name
}

output "processing_queue_url" {
  description = "SQS processing queue URL"
  value       = module.queues.processing_queue_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.ecs.alb_dns_name
}

output "alb_zone_id" {
  description = "Application Load Balancer zone ID"
  value       = module.ecs.alb_zone_id
}

output "backend_service_name" {
  description = "Backend ECS service name"
  value       = module.ecs.backend_service_name
}

output "frontend_service_name" {
  description = "Frontend ECS service name"
  value       = module.ecs.frontend_service_name
}

output "cloudwatch_log_group_backend" {
  description = "CloudWatch log group for backend"
  value       = module.ecs.backend_log_group
}

output "cloudwatch_log_group_frontend" {
  description = "CloudWatch log group for frontend"
  value       = module.ecs.frontend_log_group
}

output "virus_scanner_lambda_function_name" {
  description = "Virus scanner Lambda function name"
  value       = module.lambda.virus_scanner_function_name
}

output "application_url" {
  description = "Application URL"
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${module.ecs.alb_dns_name}"
}

output "api_url" {
  description = "API URL"
  value       = var.domain_name != "" ? "https://api.${var.domain_name}" : "http://${module.ecs.alb_dns_name}/api"
}