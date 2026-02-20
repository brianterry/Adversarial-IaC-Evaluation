terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# Transaction Processing Lambda Function
resource "aws_lambda_function" "transaction_processor" {
  function_name = "credit-card-transaction-processor"
  handler       = "index.handler"
  runtime       = "nodejs14.x"
  role          = aws_iam_role.lambda_exec.arn
  
  # Intentionally broad network configuration (V3)
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.transaction_sg.id]
  }

  tags = {
    Environment = "Development"
    Project     = "PaymentProcessing"
    Sensitivity = "High"
  }
}

# S3 Bucket for Transaction Logs (V1 & V2)
resource "aws_s3_bucket" "transaction_logs" {
  bucket = "credit-transaction-logs-${var.environment}"
  
  # Intentionally disabled public access block (V1)
  public_access_block {
    block_public_acls       = false
    block_public_policy     = false
    ignore_public_acls      = false
    restrict_public_buckets = false
  }

  # Intentionally disabled encryption (V2)
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  # Intentionally disabled logging (V5)
  logging {
    target_bucket = null
  }

  tags = {
    Name        = "Transaction Logs Bucket"
    Environment = var.environment
    Sensitivity = "Critical"
  }
}

# RDS Database for Transaction Storage (V4)
resource "aws_db_instance" "transaction_db" {
  identifier           = "transaction-database"
  engine               = "mysql"
  engine_version       = "8.0"
  instance_class       = "db.t3.medium"
  allocated_storage    = 20
  storage_type         = "gp2"
  
  # Intentionally disabled encryption (V4)
  storage_encrypted    = false

  username             = var.db_username
  password             = var.db_password

  tags = {
    Name        = "Transaction Database"
    Environment = var.environment
  }
}

# Overly Permissive Security Group (V3)
resource "aws_security_group" "transaction_sg" {
  name        = "transaction-processing-sg"
  description = "Security group for transaction processing"

  # Intentionally open ingress rules (V3)
  ingress {
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

  tags = {
    Name        = "Transaction Processing Security Group"
    Environment = var.environment
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "transaction-processor-lambda-role"

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