# CI/CD Pipeline Infrastructure Configuration
# Purpose: Sets up IAM roles and storage for automated deployment pipeline
# Environment: Production
# Last Updated: 2024-02-20

provider "aws" {
  region = var.aws_region
}

# Artifact Storage Bucket for Pipeline
resource "aws_s3_bucket" "pipeline_artifacts" {
  bucket = "${var.environment_name}-${var.project_name}-pipeline-artifacts"
  
  tags = {
    Environment = var.environment_name
    Project     = var.project_name
    Manager     = "DevOps"
    Purpose     = "CI/CD Artifact Storage"
  }
  # V1: Intentionally missing encryption configuration
  # V3: Missing logging configuration
}

# Primary CI/CD Execution Role
resource "aws_iam_role" "pipeline_execution_role" {
  name = "${var.environment_name}-${var.project_name}-pipeline-execution"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          # V4: Overly permissive trust relationship
          AWS = "*"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment_name
    Project     = var.project_name
    Purpose     = "Pipeline Execution"
  }
}

# Build Agent Role
resource "aws_iam_role" "build_agent_role" {
  name = "${var.environment_name}-${var.project_name}-build-agent"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codebuild.amazonaws.com"
        }
      }
    ]
  })
}

# V5: Deployment Role that can be assumed by Build Role
resource "aws_iam_role" "deployment_role" {
  name = "${var.environment_name}-${var.project_name}-deployment"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.build_agent_role.arn
        }
      }
    ]
  })
}

# V2: Overly permissive pipeline execution policy
resource "aws_iam_role_policy" "pipeline_execution_policy" {
  name = "pipeline-execution-policy"
  role = aws_iam_role.pipeline_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:*",
          "ec2:*",
          "iam:*",
          "lambda:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# V5: Policy allowing deployment role to assume build role
resource "aws_iam_role_policy" "deployment_policy" {
  name = "deployment-policy"
  role = aws_iam_role.deployment_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = "sts:AssumeRole"
        Resource = aws_iam_role.build_agent_role.arn
      }
    ]
  })
}