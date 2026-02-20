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

# CI/CD S3 Bucket with Intentional Security Issues (V1, V3, V4)
resource "aws_s3_bucket" "cicd_artifacts" {
  bucket = "company-cicd-artifacts-${var.environment}"
  
  tags = {
    Name        = "CI/CD Artifacts Bucket"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  # Intentional: No encryption configuration (V1)
  # Intentional: No logging configuration (V3)
  # Intentional: No public access block (V4)
}

# Security Group for Build Agents with Open Access (V2)
resource "aws_security_group" "build_agents" {
  name        = "build-agents-sg-${var.environment}"
  description = "Security group for CI/CD build agents"
  vpc_id      = var.vpc_id

  # Intentional: Overly permissive SSH access (V2)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Dangerous wide-open rule
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "Build Agents Security Group"
    Environment = var.environment
  }
}

# CI/CD Metadata Database (V5)
resource "aws_db_instance" "build_metadata" {
  identifier           = "cicd-metadata-${var.environment}"
  engine               = "postgres"
  engine_version       = "13.7"
  instance_class       = "db.t3.medium"
  allocated_storage    = 20
  
  # Intentional: No storage encryption (V5)
  
  username             = var.db_username
  password             = var.db_password
  parameter_group_name = "default.postgres13"

  tags = {
    Name        = "CI/CD Metadata Database"
    Environment = var.environment
  }
}

# IAM Role for CI/CD Pipeline
resource "aws_iam_role" "cicd_role" {
  name = "cicd-pipeline-role-${var.environment}"

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
    Name        = "CI/CD Pipeline IAM Role"
    Environment = var.environment
  }
}

# IAM Policy for CI/CD Role (Relatively Permissive)
resource "aws_iam_role_policy" "cicd_policy" {
  name = "cicd-pipeline-policy-${var.environment}"
  role = aws_iam_role.cicd_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:*",
          "ec2:*",
          "rds:*"
        ]
        Resource = "*"
      }
    ]
  })
}