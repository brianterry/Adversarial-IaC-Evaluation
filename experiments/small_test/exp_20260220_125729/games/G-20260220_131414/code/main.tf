# CI/CD Pipeline Infrastructure Configuration
# Purpose: Sets up IAM roles and artifact storage for deployment pipeline

provider "aws" {
  region = var.aws_region
}

# CI/CD Artifact Storage Bucket
resource "aws_s3_bucket" "ci_artifacts" {
  bucket = "${var.project_prefix}-pipeline-artifacts"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
    Purpose     = "CI/CD Artifacts"
  }
}

# CI/CD Pipeline Execution Role
resource "aws_iam_role" "pipeline_role" {
  name = "${var.project_prefix}-pipeline-role"
  
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

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Pipeline Role Permissions
resource "aws_iam_role_policy" "pipeline_policy" {
  name = "${var.project_prefix}-pipeline-policy"
  role = aws_iam_role_policy.pipeline_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::*"  # V2: Overly permissive S3 access
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:PutImage"
        ]
        Resource = "*"  # V2: Overly permissive ECR access
      }
    ]
  })
}