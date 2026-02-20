provider "aws" {
  region = var.aws_region
}

# CI/CD Pipeline IAM Role
resource "aws_iam_role" "cicd_pipeline_role" {
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

# S3 Bucket for CI/CD Artifacts (Intentionally Misconfigured)
resource "aws_s3_bucket" "cicd_artifacts" {
  bucket = "company-cicd-artifacts-${var.environment}"
  
  # V1: Intentional Public Access (Security Vulnerability)
  acl = "public-read"  # SECURITY ISSUE: Publicly accessible bucket

  # V2: Intentional Lack of Encryption (Security Vulnerability)
  # No server_side_encryption specified, leaving bucket unencrypted
  
  versioning {
    enabled = false
  }

  tags = {
    Name        = "CI/CD Artifacts Bucket"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# V3: Overly Permissive Security Group
resource "aws_security_group" "cicd_sg" {
  name        = "cicd-pipeline-sg"
  description = "Security group for CI/CD pipeline (INTENTIONALLY MISCONFIGURED)"

  # Unrestricted ingress rule
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # SECURITY ISSUE: Open to all IP addresses
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "CICD Pipeline Security Group"
    Environment = var.environment
  }
}

# IAM Policy for the Role (Minimally Scoped)
resource "aws_iam_role_policy" "cicd_policy" {
  name = "cicd-pipeline-policy"
  role = aws_iam_role.cicd_pipeline_role.id

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