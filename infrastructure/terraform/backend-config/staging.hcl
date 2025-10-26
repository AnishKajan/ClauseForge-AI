# Terraform backend configuration for staging environment
bucket         = "lexiscan-terraform-state-staging"
key            = "staging/terraform.tfstate"
region         = "us-east-1"
encrypt        = true
dynamodb_table = "lexiscan-terraform-locks-staging"