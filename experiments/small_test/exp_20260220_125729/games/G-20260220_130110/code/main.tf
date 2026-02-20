# Credit Card Transaction Processing Infrastructure
# WARNING: This code contains intentional vulnerabilities for security training

provider "aws" {
  region = var.aws_region
}

# Transaction Processing Lambda Function
resource "aws_lambda_function" "payment_processor" {
  filename         = "payment_processor.zip"
  function_name    = "credit-card-transaction-processor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "index.handler"
  runtime         = "nodejs16.x"
  timeout         = 30

  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tags = {
    Environment = var.environment
    Owner       = "payments-team"
    CostCenter  = "finance-123"
  }
}

# Transaction Database
resource "aws_db_instance" "transaction_db" {
  identifier           = "payment-transaction-db"
  engine              = "postgres"
  engine_version      = "13.7"
  instance_class      = "db.t3.medium"
  allocated_storage   = 100
  name                = "transactions"
  username            = var.db_username
  password            = var.db_password
  # V1: Storage encryption disabled for "performance testing"
  storage_encrypted   = false
  
  tags = {
    Environment = var.environment
    Owner       = "payments-team"
    DataClass   = "pci-sensitive"
  }
}

# Transaction Log Bucket
resource "aws_s3_bucket" "transaction_logs" {
  # V2: Bucket missing encryption configuration
  bucket = "payment-transaction-logs-${var.environment}"
  
  # V4: Missing access logging configuration
  
  tags = {
    Environment = var.environment
    Owner       = "payments-team"
    DataClass   = "financial-logs"
  }
}

# Lambda Security Group
resource "aws_security_group" "lambda_sg" {
  name        = "payment-processor-lambda-sg"
  description = "Security group for payment processing lambda"
  vpc_id      = var.vpc_id

  # V3: Overly permissive inbound rule
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS from anywhere for API testing"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Environment = var.environment
    Owner       = "payments-team"
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "payment-processor-lambda-role"

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