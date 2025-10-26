#!/bin/bash

# LocalStack initialization script
# This script runs when LocalStack container is ready

echo "Initializing LocalStack services..."

# Create S3 bucket
awslocal s3 mb s3://lexiscan-documents
awslocal s3api put-bucket-cors --bucket lexiscan-documents --cors-configuration '{
  "CORSRules": [
    {
      "AllowedOrigins": ["*"],
      "AllowedMethods": ["GET", "PUT", "POST", "DELETE"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}'

# Create SQS queue
awslocal sqs create-queue --queue-name lexiscan-processing
awslocal sqs create-queue --queue-name lexiscan-processing-dlq

# Create Secrets Manager secrets
awslocal secretsmanager create-secret \
  --name "lexiscan/api-keys" \
  --description "API keys for LexiScan application" \
  --secret-string '{
    "anthropic_api_key": "test-anthropic-key",
    "openai_api_key": "test-openai-key",
    "stripe_secret_key": "test-stripe-key"
  }'

echo "LocalStack initialization completed!"

# List created resources
echo "Created S3 buckets:"
awslocal s3 ls

echo "Created SQS queues:"
awslocal sqs list-queues

echo "Created secrets:"
awslocal secretsmanager list-secrets