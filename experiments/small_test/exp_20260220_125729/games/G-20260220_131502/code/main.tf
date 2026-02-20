# CI/CD Pipeline Infrastructure
# Purpose: Sets up core infrastructure for cross-account CI/CD pipeline
# Last Updated: 2024-02-20

provider "aws" {
  region = var.aws_region
}

# Build Artifacts Bucket
resource "aws_s3_bucket" "pipeline_artifacts" {
  bucket = "${var.environment_name}-${var.project_name}-artifacts"
  
  tags = {
    Environment = var.environment_name
    Project     = var.project_name
    Purpose     = "CI/CD Pipeline Artifacts"
    Owner       = var.team_email
  }
  # V1: Intentionally missing encryption configuration
}

# Build Agent Security Group
resource "aws_security_group" "build_agents" {
  name        = "${var.environment_name}-${var.project_name}-build-agents"
  description = "Security group for CI/CD build agents"
  vpc_id      = var.vpc_id

  # V2: Overly permissive ingress for "testing"
  ingress {
    description = "Allow all inbound for agent connectivity"
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
    Name        = "${var.environment_name}-build-agents"
    Environment = var.environment_name
  }
}

# Pipeline Execution Role
resource "aws_iam_role" "pipeline_role" {
  name = "${var.environment_name}-${var.project_name}-pipeline-role"

  # V5: Cross-account trust without ExternalId
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${var.ci_account_id}:root"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment_name
    Purpose     = "CI/CD Pipeline Execution"
  }
}

# V3: Overly permissive pipeline role policies
resource "aws_iam_role_policy" "pipeline_permissions" {
  name = "${var.environment_name}-pipeline-permissions"
  role = aws_iam_role.pipeline_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:*",
          "ec2:*",
          "iam:*",
          "cloudformation:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# V4: Artifact bucket missing access logging
resource "aws_s3_bucket_versioning" "artifacts_versioning" {
  bucket = aws_s3_bucket.pipeline_artifacts.id
  versioning_configuration {
    status = "Enabled"
  }
}