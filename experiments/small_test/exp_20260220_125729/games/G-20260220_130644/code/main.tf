```hcl
provider "aws" {
  region = var.region
}

# Transaction Processing Lambda Function
resource "aws_lambda_function" "transaction_processor" {
  function_name = "credit-card-transaction-processor-${var.environment}"
  handler       = "index.handler"
  runtime       = "nodejs14.x"
  role          = aws_iam_role.lambda_exec.arn
  
  # Simulating a real-world scenario with minimal security
  source_code_hash = filebase64sha256("lambda_function.zip")
  filename         = "lambda_function.zip"

  # Intentionally broad security group configuration (V2)
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tags = {
    Environment = var.environment
    Project     = "Credit Card Transaction Processing"
    Sensitivity = "High"
  }
}

# Intentionally Insecure S3 Bucket for Transaction Logs (V1, V3)
resource "aws_s3_bucket" "transaction_logs" {
  bucket = "credit-card-transactions-${var.environment}"
  
  # No encryption configuration (V1)
  # No access logging configuration (V3)

  tags = {
    Environment = var.environment
    DataType    = "Financial Transactions"
  }
}

# Intentionally Permissive Security Group (V2)
resource "aws_security_group" "lambda_sg" {
  name        = "credit-card-processor-sg-${var.environment}"
  description = "Security group for credit card transaction processing lambda"

  # Unrestricted ingress rule (V2)
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
    Environment = var.environment
    Purpose     = "Lambda Network Access"
  }
}

# IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_exec" {
  name = "credit-card-processor-lambda-role-${var.environment}"

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

# Minimal IAM Policy (demonstrating least privilege principle)
resource "aws_iam_role_policy" "lambda_exec_policy" {
  name = "credit-card-processor-lambda-policy-${var.environment}"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}
```