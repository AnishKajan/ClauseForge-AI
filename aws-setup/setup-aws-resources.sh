#!/bin/bash

# LexiScan AWS Resources Setup Script
# This script creates the necessary AWS resources for LexiScan

set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
BUCKET_NAME="lexiscan-documents-${ENVIRONMENT}"
QUEUE_NAME="lexiscan-processing-${ENVIRONMENT}"
DLQ_NAME="lexiscan-processing-dlq-${ENVIRONMENT}"

echo "Setting up AWS resources for LexiScan in region: $REGION"
echo "Environment: $ENVIRONMENT"

# Check if AWS CLI is installed and configured
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it first."
    exit 1
fi

# Verify AWS credentials
echo "Verifying AWS credentials..."
aws sts get-caller-identity > /dev/null || {
    echo "Error: AWS credentials not configured. Run 'aws configure' first."
    exit 1
}

# Create S3 bucket for document storage
echo "Creating S3 bucket: $BUCKET_NAME"
if aws s3api head-bucket --bucket "$BUCKET_NAME" 2>/dev/null; then
    echo "Bucket $BUCKET_NAME already exists"
else
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region "$REGION" \
        --create-bucket-configuration LocationConstraint="$REGION" 2>/dev/null || \
    aws s3api create-bucket \
        --bucket "$BUCKET_NAME" \
        --region us-east-1  # us-east-1 doesn't need LocationConstraint
    
    # Enable versioning
    aws s3api put-bucket-versioning \
        --bucket "$BUCKET_NAME" \
        --versioning-configuration Status=Enabled
    
    # Enable server-side encryption
    aws s3api put-bucket-encryption \
        --bucket "$BUCKET_NAME" \
        --server-side-encryption-configuration '{
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    }
                }
            ]
        }'
    
    # Block public access
    aws s3api put-public-access-block \
        --bucket "$BUCKET_NAME" \
        --public-access-block-configuration \
        BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
    
    echo "S3 bucket $BUCKET_NAME created successfully"
fi

# Create SQS Dead Letter Queue
echo "Creating SQS Dead Letter Queue: $DLQ_NAME"
DLQ_URL=$(aws sqs create-queue \
    --queue-name "$DLQ_NAME" \
    --region "$REGION" \
    --attributes '{
        "MessageRetentionPeriod": "1209600",
        "VisibilityTimeoutSeconds": "60"
    }' \
    --query 'QueueUrl' --output text)

DLQ_ARN=$(aws sqs get-queue-attributes \
    --queue-url "$DLQ_URL" \
    --attribute-names QueueArn \
    --query 'Attributes.QueueArn' --output text)

echo "Dead Letter Queue created: $DLQ_URL"

# Create SQS Queue for document processing
echo "Creating SQS Queue: $QUEUE_NAME"
QUEUE_URL=$(aws sqs create-queue \
    --queue-name "$QUEUE_NAME" \
    --region "$REGION" \
    --attributes "{
        \"MessageRetentionPeriod\": \"1209600\",
        \"VisibilityTimeoutSeconds\": \"300\",
        \"RedrivePolicy\": \"{\\\"deadLetterTargetArn\\\":\\\"$DLQ_ARN\\\",\\\"maxReceiveCount\\\":3}\"
    }" \
    --query 'QueueUrl' --output text)

echo "SQS Queue created: $QUEUE_URL"

# Create IAM policies
echo "Creating IAM policies..."

# S3 Access Policy
aws iam create-policy \
    --policy-name "LexiScan-S3-Access-Policy-${ENVIRONMENT}" \
    --policy-document file://iam-policies.json \
    --path "/lexiscan/" 2>/dev/null || echo "S3 policy already exists"

# Create Secrets Manager secrets
echo "Creating Secrets Manager secrets..."

# Create secret for API keys
SECRET_VALUE=$(cat <<EOF
{
    "anthropic_api_key": "REPLACE_WITH_ACTUAL_KEY",
    "openai_api_key": "REPLACE_WITH_ACTUAL_KEY",
    "stripe_secret_key": "REPLACE_WITH_ACTUAL_KEY",
    "stripe_webhook_secret": "REPLACE_WITH_ACTUAL_KEY",
    "jwt_secret": "$(openssl rand -base64 32)",
    "nextauth_secret": "$(openssl rand -base64 32)"
}
EOF
)

aws secretsmanager create-secret \
    --name "lexiscan/api-keys-${ENVIRONMENT}" \
    --description "API keys for LexiScan ${ENVIRONMENT} environment" \
    --secret-string "$SECRET_VALUE" \
    --region "$REGION" 2>/dev/null || echo "Secret already exists"

# Output configuration
echo ""
echo "=== AWS Resources Created Successfully ==="
echo ""
echo "S3 Bucket: $BUCKET_NAME"
echo "SQS Queue URL: $QUEUE_URL"
echo "SQS DLQ URL: $DLQ_URL"
echo "Region: $REGION"
echo ""
echo "=== Next Steps ==="
echo "1. Update your .env file with the following values:"
echo "   S3_BUCKET_NAME=$BUCKET_NAME"
echo "   SQS_QUEUE_URL=$QUEUE_URL"
echo "   SQS_DLQ_URL=$DLQ_URL"
echo "   AWS_REGION=$REGION"
echo ""
echo "2. Update the Secrets Manager secret with your actual API keys:"
echo "   aws secretsmanager update-secret --secret-id lexiscan/api-keys-${ENVIRONMENT} --secret-string '{...}'"
echo ""
echo "3. Create IAM roles and attach the policies from iam-policies.json"
echo "4. Configure Stripe webhook endpoint: https://your-domain.com/api/webhooks/stripe"
echo ""
echo "Setup completed successfully!"