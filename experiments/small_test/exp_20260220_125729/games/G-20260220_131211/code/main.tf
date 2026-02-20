# Credit Card Transaction Processing Infrastructure
# Last updated: 2024-02-20
# Purpose: Handles credit card payment processing through Lambda with RDS storage

provider "aws" {
  region = var.aws_region
}

# Lambda function for processing credit card transactions
resource "aws_lambda_function" "payment_processor" {
  filename         = "payment_processor.zip"
  function_name    = "credit-card-payment-processor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "index.handler"
  runtime         = "nodejs18.x"

  environment {
    variables = {
      RDS_CLUSTER_ENDPOINT = aws_rds_cluster.transaction_history.endpoint
      TRANSACTION_BUCKET   = aws_s3_bucket.transaction_logs.id
    }
  }

  tags = {
    Environment = var.environment
    Department  = "Finance"
    Purpose     = "Payment Processing"
  }
}

# RDS Cluster for transaction history
# V1: Missing encryption configuration
resource "aws_rds_cluster" "transaction_history" {
  cluster_identifier  = "payment-transaction-history"
  database_name      = "payments"
  master_username    = var.db_username
  master_password    = var.db_password
  engine            = "aurora-mysql"
  engine_version    = "5.7.mysql_aurora.2.11.2"
  
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.payment_subnet_group.name
  
  # Storage encryption intentionally omitted for V1
}

# S3 bucket for transaction logs
# V3: Missing logging configuration
resource "aws_s3_bucket" "transaction_logs" {
  bucket = "payment-transaction-logs-${var.environment}"
  
  tags = {
    Environment = var.environment
    Purpose     = "Payment Transaction Logs"
  }
}

# V2: Overly permissive security group
resource "aws_security_group" "lambda_sg" {
  name        = "payment-lambda-sg"
  description = "Security group for payment processing Lambda"
  vpc_id      = var.vpc_id

  ingress {
    description = "Allow all inbound for testing"
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # V2: Overly permissive
  }

  tags = {
    Name = "payment-lambda-sg"
    Environment = var.environment
  }
}

# Supporting resources
resource "aws_db_subnet_group" "payment_subnet_group" {
  name       = "payment-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Environment = var.environment
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "payment-rds-sg"
  description = "Security group for payment RDS cluster"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id]
  }
}