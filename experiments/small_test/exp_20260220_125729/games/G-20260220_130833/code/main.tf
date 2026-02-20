# CI/CD Infrastructure Configuration
# Author: DevOps Team
# Purpose: Manage CI/CD Pipeline Resources

provider "aws" {
  region = var.aws_region
}

# IAM Role for CI/CD Pipeline
resource "aws_iam_role" "cicd_role" {
  name = "cicd-pipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = "Development"
    ManagedBy   = "Terraform"
    Project     = "CI/CD Pipeline"
  }
}

# S3 Bucket for CI/CD Artifacts - VULNERABILITY V1: No Encryption
resource "aws_s3_bucket" "cicd_artifacts" {
  bucket = "my-company-cicd-artifacts-${var.environment}"
  
  # VULNERABILITY: Missing server-side encryption configuration
  # This deliberately omits encryption to simulate a real-world oversight

  tags = {
    Name        = "CI/CD Artifacts Bucket"
    Environment = var.environment
    Sensitivity = "Medium"
  }
}

# Security Group for CI/CD Runner - VULNERABILITY V2: Overly Permissive
resource "aws_security_group" "cicd_runner" {
  name        = "cicd-runner-sg"
  description = "Security group for CI/CD runner instances"

  # VULNERABILITY: Allows SSH access from anywhere
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "CI/CD Runner Security Group"
    Environment = var.environment
  }
}

# IAM Policy for CI/CD Role
resource "aws_iam_role_policy" "cicd_policy" {
  name = "cicd-pipeline-policy"
  role = aws_iam_role.cicd_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.cicd_artifacts.arn,
          "${aws_s3_bucket.cicd_artifacts.arn}/*"
        ]
      }
    ]
  })
}