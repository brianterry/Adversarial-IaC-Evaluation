provider "aws" {
  region = var.region
}

# S3 Bucket for Transaction Logs (V1: Public Access)
resource "aws_s3_bucket" "transaction_logs" {
  bucket = "credit-transaction-logs-${random_id.bucket_suffix.hex}"
  acl    = "public-read"  # VULNERABILITY: Public read access

  tags = {
    Name        = "Credit Card Transaction Logs"
    Environment = var.environment
    Sensitivity = "High"
  }
}

# Security Group for Lambda VPC Access (V2: Unrestricted Ingress)
resource "aws_security_group" "lambda_network" {
  name        = "credit-transaction-lambda-sg"
  description = "Security group for credit transaction processing lambda"

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # VULNERABILITY: Wide open ingress
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "Credit Transaction Lambda Network"
    Environment = var.environment
  }
}

# Unencrypted S3 Bucket for Transaction Storage (V3: No Encryption)
resource "aws_s3_bucket" "transaction_storage" {
  bucket = "credit-card-transactions-${random_id.bucket_suffix.hex}"
  
  # VULNERABILITY: No encryption configuration
  
  versioning {
    enabled = true
  }

  tags = {
    Name        = "Credit Card Transactions Storage"
    Environment = var.environment
    Sensitivity = "Critical"
  }
}

# RDS Database without Encryption (V5: Unencrypted DB)
resource "aws_db_instance" "transaction_db" {
  identifier           = "credit-transaction-db"
  allocated_storage    = 20
  engine               = "postgres"
  engine_version       = "13.7"
  instance_class       = "db.t3.medium"
  
  # VULNERABILITY: No storage encryption
  
  username             = var.db_username
  password             = var.db_password
  parameter_group_name = "default.postgres13"

  tags = {
    Name        = "Credit Transaction Database"
    Environment = var.environment
  }
}

# S3 Bucket without Logging (V4: Disabled Logging)
resource "aws_s3_bucket" "transaction_audit" {
  bucket = "financial-transactions-${random_id.bucket_suffix.hex}"
  
  # VULNERABILITY: No logging configuration
  
  tags = {
    Name        = "Financial Transactions Audit"
    Environment = var.environment
    Sensitivity = "High"
  }
}

# Lambda Function for Processing Transactions
resource "aws_lambda_function" "transaction_processor" {
  function_name = "credit-transaction-processor"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "index.handler"
  runtime       = "nodejs14.x"

  filename         = "lambda_function.zip"
  source_code_hash = filebase64sha256("lambda_function.zip")

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.lambda_network.id]
  }

  tags = {
    Name        = "Credit Card Transaction Processor"
    Environment = var.environment
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "credit-transaction-lambda-role"

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

# Random ID for Unique Bucket Names
resource "random_id" "bucket_suffix" {
  byte_length = 8
}