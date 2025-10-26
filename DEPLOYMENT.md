# LexiScan Deployment Guide

This guide covers deploying LexiScan to AWS using Terraform and CI/CD pipelines.

## Prerequisites

### Required Tools
- [AWS CLI](https://aws.amazon.com/cli/) v2.0+
- [Terraform](https://www.terraform.io/) v1.6+
- [Docker](https://www.docker.com/) v20.0+
- [Node.js](https://nodejs.org/) v18+
- [Python](https://www.python.org/) v3.11+

### AWS Setup
1. Configure AWS credentials:
   ```bash
   aws configure
   ```

2. Create S3 buckets for Terraform state:
   ```bash
   aws s3 mb s3://lexiscan-terraform-state-staging
   aws s3 mb s3://lexiscan-terraform-state-production
   ```

3. Create DynamoDB tables for state locking:
   ```bash
   aws dynamodb create-table \
     --table-name lexiscan-terraform-locks-staging \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5

   aws dynamodb create-table \
     --table-name lexiscan-terraform-locks-production \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
   ```

## Environment Configuration

### Staging Environment
- **Purpose**: Testing and validation
- **Resources**: Minimal (t3.micro instances)
- **Domain**: staging.lexiscan.ai (optional)
- **Monitoring**: Basic CloudWatch

### Production Environment
- **Purpose**: Live application
- **Resources**: Production-ready (t3.small+ instances)
- **Domain**: lexiscan.ai
- **Monitoring**: Full observability stack
- **Backup**: 7-day retention

## Deployment Methods

### 1. Automated CI/CD (Recommended)

The GitHub Actions pipeline automatically deploys on:
- **Staging**: Push to `develop` branch
- **Production**: Push to `main` branch

#### Required GitHub Secrets
```bash
# AWS Configuration
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_ACCOUNT_ID

# Application Secrets
JWT_SECRET
ANTHROPIC_API_KEY
OPENAI_API_KEY
STRIPE_SECRET_KEY

# Monitoring
ALERT_EMAIL

# Domain (production only)
DOMAIN_NAME
```

#### Pipeline Stages
1. **Test**: Run backend and frontend tests
2. **Security**: Vulnerability scanning with Trivy
3. **Build**: Create and push Docker images to ECR
4. **Deploy**: Apply Terraform infrastructure
5. **Verify**: Run smoke tests
6. **Rollback**: Automatic rollback on failure

### 2. Manual Deployment

Use the deployment script for manual deployments:

```bash
# Deploy to staging
./scripts/deploy.sh -e staging

# Deploy to production
./scripts/deploy.sh -e production

# Dry run (show plan without applying)
./scripts/deploy.sh -e staging --dry-run

# Skip tests and build (use existing images)
./scripts/deploy.sh -e production --skip-tests --skip-build
```

### 3. Direct Terraform

For advanced users who want full control:

```bash
cd infrastructure/terraform

# Initialize
terraform init -backend-config=backend-config/staging.hcl

# Plan
terraform plan -var-file=environments/staging.tfvars

# Apply
terraform apply -var-file=environments/staging.tfvars
```

## Infrastructure Components

### Core Services
- **ECS Fargate**: Container orchestration
- **Application Load Balancer**: Traffic distribution
- **RDS PostgreSQL**: Primary database with pgvector
- **ElastiCache Redis**: Caching and rate limiting
- **S3**: Document storage
- **SQS**: Asynchronous processing queues

### Security
- **VPC**: Network isolation
- **Security Groups**: Firewall rules
- **WAF**: Web application firewall
- **Secrets Manager**: Secure credential storage
- **IAM**: Fine-grained permissions

### Monitoring
- **CloudWatch**: Logs and metrics
- **OpenTelemetry**: Distributed tracing
- **Health Checks**: Service availability monitoring
- **Alarms**: Automated alerting

### Optional Components
- **Route53**: DNS management
- **ACM**: SSL certificates
- **Lambda**: Virus scanning functions

## Configuration

### Environment Variables

#### Backend Configuration
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0

# AI Services
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
EMBEDDING_PROVIDER=openai
LLM_PROVIDER=anthropic

# AWS Services
AWS_REGION=us-east-1
S3_BUCKET_NAME=lexiscan-documents-prod
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/...

# Security
JWT_SECRET=your-secret-key
SECRET_KEY=your-app-secret

# Monitoring
OTEL_EXPORTER_OTLP_ENDPOINT=https://...
ENABLE_AUDIT_LOGGING=true
```

#### Frontend Configuration
```bash
# API Configuration
NEXT_PUBLIC_API_URL=https://api.lexiscan.ai
NEXT_PUBLIC_APP_URL=https://lexiscan.ai

# Authentication
NEXTAUTH_URL=https://lexiscan.ai
NEXTAUTH_SECRET=your-nextauth-secret

# Monitoring
NEXT_PUBLIC_SENTRY_DSN=https://...
```

### Terraform Variables

Key variables in `environments/*.tfvars`:

```hcl
# Environment
environment = "production"
aws_region  = "us-east-1"

# Networking
vpc_cidr = "10.1.0.0/16"

# Database
db_instance_class = "db.t3.small"
db_allocated_storage = 100

# Compute
backend_cpu = 512
backend_memory = 1024
backend_desired_count = 2

# Domain
domain_name = "lexiscan.ai"
```

## Monitoring and Observability

### Health Checks
- **Basic**: `/api/health`
- **Detailed**: `/api/health/detailed`
- **Readiness**: `/api/ready`
- **Liveness**: `/api/live`
- **Metrics**: `/api/metrics`

### Logging
- **Format**: Structured JSON logs
- **Destination**: CloudWatch Logs
- **Retention**: 30 days (configurable)
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Metrics
- **Business KPIs**: Document uploads, analyses, queries
- **System Metrics**: CPU, memory, disk, network
- **Application Metrics**: Response times, error rates
- **Custom Metrics**: OpenTelemetry integration

### Alerting
- **High Error Rate**: >5% error rate for 5 minutes
- **High Response Time**: >2s P95 for 5 minutes
- **Resource Usage**: >80% CPU/memory for 10 minutes
- **Service Unavailable**: Health check failures

## Security Considerations

### Network Security
- Private subnets for application and database
- Security groups with minimal required access
- VPC endpoints for AWS service communication
- WAF rules for common attack patterns

### Data Security
- Encryption at rest (S3, RDS, EBS)
- Encryption in transit (TLS 1.2+)
- Secrets stored in AWS Secrets Manager
- Regular security scanning with Trivy

### Access Control
- IAM roles with least privilege
- Multi-factor authentication for AWS console
- Service-to-service authentication with IAM roles
- API rate limiting and authentication

### Compliance
- Audit logging for all user actions
- Data retention policies
- GDPR/CCPA compliance features
- SOC 2 Type II controls

## Troubleshooting

### Common Issues

#### Deployment Failures
```bash
# Check Terraform state
terraform show

# View ECS service events
aws ecs describe-services --cluster lexiscan-prod-cluster --services lexiscan-prod-backend

# Check CloudWatch logs
aws logs tail /aws/ecs/lexiscan-backend --follow
```

#### Application Issues
```bash
# Check health endpoints
curl https://api.lexiscan.ai/health/detailed

# View application logs
aws logs filter-log-events --log-group-name /aws/ecs/lexiscan-backend --filter-pattern "ERROR"

# Check database connectivity
aws rds describe-db-instances --db-instance-identifier lexiscan-prod-db
```

#### Performance Issues
```bash
# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=lexiscan-prod-backend \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 300 \
  --statistics Average
```

### Rollback Procedures

#### Automatic Rollback
The CI/CD pipeline includes automatic rollback on deployment failure.

#### Manual Rollback
```bash
# Rollback to previous ECS task definition
aws ecs update-service \
  --cluster lexiscan-prod-cluster \
  --service lexiscan-prod-backend \
  --task-definition lexiscan-backend:PREVIOUS_REVISION

# Rollback Terraform changes
terraform apply -var-file=environments/production.tfvars -target=module.ecs
```

## Scaling

### Horizontal Scaling
```bash
# Scale ECS services
aws ecs update-service \
  --cluster lexiscan-prod-cluster \
  --service lexiscan-prod-backend \
  --desired-count 4
```

### Vertical Scaling
Update Terraform variables and redeploy:
```hcl
backend_cpu = 1024
backend_memory = 2048
```

### Database Scaling
```bash
# Scale RDS instance
aws rds modify-db-instance \
  --db-instance-identifier lexiscan-prod-db \
  --db-instance-class db.t3.medium \
  --apply-immediately
```

## Maintenance

### Regular Tasks
- **Weekly**: Review CloudWatch alarms and logs
- **Monthly**: Update dependencies and security patches
- **Quarterly**: Review and optimize costs
- **Annually**: Security audit and compliance review

### Backup and Recovery
- **Database**: Automated daily backups with 7-day retention
- **Application Data**: S3 versioning and lifecycle policies
- **Infrastructure**: Terraform state stored in S3 with versioning
- **Disaster Recovery**: Multi-AZ deployment with automated failover

## Cost Optimization

### Staging Environment
- Use t3.micro instances
- Single AZ deployment
- Minimal backup retention
- Estimated cost: $50-100/month

### Production Environment
- Use t3.small+ instances
- Multi-AZ deployment
- Full backup and monitoring
- Estimated cost: $200-500/month

### Cost Monitoring
- Set up billing alerts
- Use AWS Cost Explorer
- Regular resource utilization review
- Consider Reserved Instances for stable workloads

## Support

For deployment issues:
1. Check this documentation
2. Review CloudWatch logs
3. Check GitHub Issues
4. Contact the development team

---

**Note**: This deployment guide assumes familiarity with AWS services and Terraform. For production deployments, consider engaging with AWS Professional Services or a certified partner.