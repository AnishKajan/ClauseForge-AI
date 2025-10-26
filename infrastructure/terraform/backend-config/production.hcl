# Terraform backend configuration for production environment
bucket         = "lexiscan-terraform-state-production"
key            = "production/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "lexiscan-terraform-locks-production"