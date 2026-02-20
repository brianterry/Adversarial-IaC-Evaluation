# Credit Card Transaction Processing Infrastructure
# Last updated: 2024-02
# Team: Payments Platform

provider "aws" {
  region = var.aws_region
}

# VPC for secure processing environment
resource "aws_vpc" "payment_vpc" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "payment-processing-vpc"
    Environment = var.environment
    Compliance  = "PCI-DSS"
  }
}

# RDS Cluster for transaction storage
resource "aws_rds_cluster" "payment_db" {
  cluster_identifier     = "payment-processing-${var.environment}"
  engine                = "aurora-postgresql"
  database_name         = "transactions"
  master_username       = var.db_username
  master_password       = var.db_password
  db_subnet_group_name  = aws_db_subnet_group.payment_db.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  # V1: Storage encryption disabled for "development speed"
  storage_encrypted     = false
  
  tags = {
    Name        = "payment-db"
    Environment = var.environment
    Compliance  = "PCI-DSS"
  }
}

# S3 bucket for transaction logs
resource "aws_s3_bucket" "transaction_logs" {
  bucket = "payment-transaction-logs-${var.environment}-${random_string.suffix.result}"
  
  # V2: Missing encryption configuration
  # V4: Missing logging configuration
  
  tags = {
    Name        = "payment-logs"
    Environment = var.environment
    DataType    = "TransactionLogs"
  }
}

# Lambda function for processing
resource "aws_lambda_function" "payment_processor" {
  filename         = "payment_processor.zip"
  function_name    = "payment-processor-${var.environment}"
  role            = aws_iam_role.lambda_role.arn
  handler         = "index.handler"
  runtime         = "nodejs18.x"
  
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      DB_ENDPOINT = aws_rds_cluster.payment_db.endpoint
      LOG_BUCKET  = aws_s3_bucket.transaction_logs.id
    }
  }
}

# Security group for Lambda
resource "aws_security_group" "lambda_sg" {
  name        = "payment-processor-lambda-sg"
  description = "Security group for payment processing Lambda"
  vpc_id      = aws_vpc.payment_vpc.id

  # V3: Overly permissive ingress
  ingress {
    description = "Allow all inbound for testing"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "random_string" "suffix" {
  length  = 8
  special = false
  upper   = false
}