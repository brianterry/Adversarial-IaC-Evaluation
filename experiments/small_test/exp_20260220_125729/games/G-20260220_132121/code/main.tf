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

# CI/CD Artifact Storage Bucket (V1: Unencrypted S3 Bucket)
resource "aws_s3_bucket" "cicd_artifacts" {
  bucket = "company-${var.project_name}-cicd-artifacts-${var.environment}"
  
  tags = {
    Name        = "CI/CD Artifacts Bucket"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# V3: Public Access Configuration (Intentionally Permissive)
resource "aws_s3_bucket_public_access_block" "cicd_artifacts" {
  bucket = aws_s3_bucket.cicd_artifacts.id

  # VULNERABILITY: Deliberately disabled public access blocks
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# CI/CD Security Group (V2: Overly Permissive)
resource "aws_security_group" "pipeline_access" {
  name        = "${var.project_name}-pipeline-sg"
  description = "Security group for CI/CD pipeline access"
  vpc_id      = var.vpc_id

  # VULNERABILITY: Open SSH access from anywhere
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "CI/CD Pipeline Access"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Build Metadata Database (V5: Unencrypted Database)
resource "aws_db_instance" "build_metadata" {
  identifier           = "${var.project_name}-build-metadata"
  engine               = "postgres"
  engine_version       = "13.7"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  username             = var.db_username
  password             = var.db_password

  # VULNERABILITY: No explicit encryption
  # storage_encrypted is not set, defaulting to false

  tags = {
    Name        = "Build Metadata Database"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Role for CI/CD Pipeline
resource "aws_iam_role" "cicd_role" {
  name = "${var.project_name}-cicd-role"

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
    Name        = "CI/CD Pipeline Role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for CI/CD Role
resource "aws_iam_role_policy_attachment" "cicd_policy" {
  role       = aws_iam_role.cicd_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonS3FullAccess"
}