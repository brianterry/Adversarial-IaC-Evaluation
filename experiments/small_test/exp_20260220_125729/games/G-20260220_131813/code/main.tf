provider "aws" {
  region = var.region
}

# Lambda function for processing credit card transactions
resource "aws_lambda_function" "transaction_processor" {
  function_name = "credit-card-transaction-processor"
  handler       = "index.handler"
  runtime       = "nodejs14.x"
  role          = aws_iam_role.lambda_exec.arn
  
  # Simulating a real-world transaction processing function
  filename         = "lambda_function.zip"
  source_code_hash = filebase64sha256("lambda_function.zip")

  tags = {
    Environment = "Production"
    Project     = "Financial-Services"
    ManagedBy   = "Terraform"
  }
}

# S3 Bucket for Transaction Logs (V1: No Encryption)
resource "aws_s3_bucket" "transaction_logs" {
  bucket = "credit-card-transactions-logs-${var.environment}"
  
  # VULNERABILITY: No encryption configuration
  # This violates AVD-AWS-0086 - S3 Bucket Lacks Encryption
  
  tags = {
    Name        = "Credit Card Transaction Logs"
    Environment = var.environment
    Sensitivity = "High"
  }
}

# Security Group with Overly Permissive Rules (V2: Global Ingress)
resource "aws_security_group" "lambda_network" {
  name        = "credit-card-transaction-sg"
  description = "Security group for transaction processing lambda"
  vpc_id      = var.vpc_id

  # VULNERABILITY: Allows all inbound traffic
  # This violates AVD-AWS-0024 - Global Ingress
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
    Name = "Transaction Processing Network"
  }
}

# IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_exec" {
  name = "credit-card-transaction-lambda-role"

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

# IAM Policy for Lambda to Write Logs
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
  role       = aws_iam_role.lambda_exec.name
}