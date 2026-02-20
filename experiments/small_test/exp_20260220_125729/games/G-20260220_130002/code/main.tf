# Credit Card Transaction Processing Infrastructure
# Purpose: Process credit card payments and store transaction records
# Environment: Production
# Last Updated: 2024

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

# Lambda function for processing credit card transactions
resource "aws_lambda_function" "payment_processor" {
  filename         = "payment_processor.zip"
  function_name    = "credit-card-payment-processor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "index.handler"
  runtime         = "nodejs18.x"

  environment {
    variables = {
      RDS_CLUSTER_ENDPOINT = aws_rds_cluster.payment_history.endpoint
      RECEIPT_BUCKET       = aws_s3_bucket.transaction_receipts.bucket
    }
  }

  tags = var.common_tags
}

# RDS Cluster for transaction history
resource "aws_rds_cluster" "payment_history" {
  cluster_identifier  = "payment-history-${var.environment}"
  engine             = "aurora-postgresql"
  database_name      = "payments"
  master_username    = var.db_username
  master_password    = var.db_password
  # V1: Missing encryption for sensitive financial data
  storage_encrypted  = false  
  
  tags = merge(var.common_tags, {
    DataClassification = "Financial"
  })
}

# S3 Bucket for storing transaction receipts
resource "aws_s3_bucket" "transaction_receipts" {
  # V2: Bucket created without encryption
  bucket = "payment-receipts-${data.aws_caller_identity.current.account_id}"
  
  # V3: Missing logging configuration for audit requirements
  
  tags = merge(var.common_tags, {
    DataClassification = "Financial"
  })
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "payment_processor_lambda_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}