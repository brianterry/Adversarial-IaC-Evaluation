# CI/CD Pipeline Infrastructure Configuration
# Purpose: Sets up IAM roles and artifact storage for deployment pipeline

provider "aws" {
  region = var.aws_region
}

# CI/CD Artifact Storage Bucket
resource "aws_s3_bucket" "ci_artifacts" {
  bucket = "${var.project_prefix}-cicd-artifacts-${var.environment}"

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
    Purpose     = "CI/CD artifact storage"
  }
}

# CI/CD Pipeline Execution Role
resource "aws_iam_role" "pipeline_role" {
  name = "${var.project_prefix}-cicd-pipeline-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "codepipeline.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }
}

# Pipeline Role Policy
resource "aws_iam_role_policy" "pipeline_policy" {
  name = "${var.project_prefix}-cicd-pipeline-policy"
  role = aws_iam_role_policy.pipeline_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
        ]
        Resource = [
          "arn:aws:s3:::*"  # Overly permissive for training purposes
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "codecommit:CancelUploadArchive",
          "codecommit:GetBranch",
          "codecommit:GetCommit",
          "codecommit:GetUploadArchiveStatus",
          "codecommit:UploadArchive"
        ]
        Resource = "*"  # Overly permissive for training purposes
      }
    ]
  })
}