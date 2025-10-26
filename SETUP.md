# LexiScan Setup Guide

This guide covers the prerequisites and environment setup for the LexiScan AI Contract Analyzer platform.

## Prerequisites Checklist

### 1. Runtime Requirements

#### Python 3.11+
- ✅ Current version: Python 3.11.9 (already installed)
- Required for FastAPI backend and AI processing

#### Node.js 20+
- ❌ Current version: v18.20.8 (needs upgrade)
- Required for Next.js frontend

**To upgrade Node.js:**
```bash
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
nvm alias default 20

# Or using Homebrew on macOS
brew install node@20
brew link --overwrite node@20
```

#### Docker & Docker Compose
- ✅ Docker version 28.0.4 (already installed)
- ✅ Docker Compose version v2.34.0 (already installed)
- Required for local development environment

### 2. AWS Services Setup

#### Required AWS Services
- **S3**: Document storage with encryption
- **SQS**: Asynchronous processing queue
- **Textract**: OCR for scanned documents
- **Secrets Manager**: Secure credential storage
- **RDS**: PostgreSQL with pgvector (production)

#### IAM Roles and Policies

Create the following IAM roles with appropriate policies:

**LexiScan-S3-Access-Role**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:GetObjectVersion",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::lexiscan-documents/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::lexiscan-documents"
    }
  ]
}
```

**LexiScan-SQS-Access-Role**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:ChangeMessageVisibility"
      ],
      "Resource": "arn:aws:sqs:*:*:lexiscan-*"
    }
  ]
}
```

**LexiScan-Textract-Access-Role**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "textract:DetectDocumentText",
        "textract:AnalyzeDocument",
        "textract:StartDocumentTextDetection",
        "textract:GetDocumentTextDetection"
      ],
      "Resource": "*"
    }
  ]
}
```

**LexiScan-Secrets-Access-Role**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:lexiscan/*"
    }
  ]
}
```

### 3. Third-Party API Keys

#### Stripe Configuration
1. Create a Stripe account at https://stripe.com
2. Navigate to API Keys section
3. Copy the following keys:
   - **Publishable Key** (starts with `pk_`)
   - **Secret Key** (starts with `sk_`)
   - **Webhook Signing Secret** (starts with `whsec_`)

**Webhook Endpoints to Configure:**
- `https://your-domain.com/api/webhooks/stripe`
- Events to listen for:
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`

#### Anthropic Claude API
1. Sign up at https://console.anthropic.com
2. Generate API key from the API Keys section
3. Key format: `sk-ant-api03-...`

**Alternative: AWS Bedrock**
If using AWS Bedrock instead of direct Anthropic API:
1. Enable Claude models in AWS Bedrock console
2. Ensure IAM role has `bedrock:InvokeModel` permission
3. Available models:
   - `anthropic.claude-3-sonnet-20240229-v1:0`
   - `anthropic.claude-3-opus-20240229-v1:0`

### 4. Environment Variables

Create a `.env.example` file with all required environment variables:

```bash
# Database
DATABASE_URL=postgresql://lexiscan:password@localhost:5432/lexiscan
REDIS_URL=redis://localhost:6379

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
S3_BUCKET_NAME=lexiscan-documents
SQS_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789/lexiscan-processing

# AI Services
ANTHROPIC_API_KEY=sk-ant-api03-...
# OR for AWS Bedrock
USE_BEDROCK=false
BEDROCK_REGION=us-east-1

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Application
JWT_SECRET=your-super-secret-jwt-key
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000

# Development
NODE_ENV=development
LOG_LEVEL=debug
```

## Quick Setup Commands

After installing the prerequisites, run these commands to set up the development environment:

```bash
# 1. Clone and setup project structure (will be created in task 1)
# 2. Install dependencies (will be handled in task 1)
# 3. Copy environment variables
cp .env.example .env
# Edit .env with your actual values

# 4. Start local development services
docker-compose up -d postgres redis localstack

# 5. Run database migrations (will be created in task 2)
# python -m alembic upgrade head

# 6. Start development servers (will be configured in task 1)
# Backend: uvicorn main:app --reload --port 8000
# Frontend: npm run dev
```

## Verification Steps

Run these commands to verify your setup:

```bash
# Check Python version
python3 --version  # Should be 3.11+

# Check Node version
node --version      # Should be 20+

# Check Docker
docker --version
docker-compose --version

# Test AWS CLI (if installed)
aws sts get-caller-identity

# Test API keys (after setup)
curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" https://api.anthropic.com/v1/messages
```

## Next Steps

Once all prerequisites are met:
1. Proceed to Task 1: Set up project structure and development environment
2. Configure local Docker Compose services
3. Set up database with pgvector extension
4. Begin implementing core services

## Troubleshooting

### Common Issues

**Node.js Version Conflicts**
- Use nvm to manage multiple Node versions
- Ensure your shell profile loads nvm correctly

**Docker Permission Issues**
- Add your user to the docker group: `sudo usermod -aG docker $USER`
- Restart your shell session

**AWS Credentials**
- Use AWS CLI: `aws configure`
- Or set environment variables directly
- For local development, consider using LocalStack

**Database Connection Issues**
- Ensure PostgreSQL is running in Docker
- Check connection string format
- Verify network connectivity between containers