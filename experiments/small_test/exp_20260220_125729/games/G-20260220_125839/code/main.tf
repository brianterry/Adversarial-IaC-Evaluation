# PHI Data Storage Infrastructure
# ENVIRONMENT: Production
# COMPLIANCE SCOPE: HIPAA

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

# KMS Key for PHI encryption
resource "aws_kms_key" "phi_encryption_key" {
  description             = "KMS key for PHI data encryption"
  enable_key_rotation     = true
  deletion_window_in_days = 30

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action   = "kms:*"
        Resource = "*"
      }
    ]
  })

  tags = merge(
    var.common_tags,
    {
      Name        = "phi-encryption-key"
      Environment = "production"
      PHIData     = "true"
    }
  )
}

resource "aws_s3_bucket" "phi_storage" {
  bucket = "${var.environment}-${var.project_name}-phi-storage-${data.aws_caller_identity.current.account_id}"

  tags = merge(
    var.common_tags,
    {
      Name        = "phi-storage"
      Environment = "production"
      PHIData     = "true"
    }
  )
}

# Deprecated encryption configuration
resource "aws_s3_bucket_server_side_encryption_configuration" "phi_storage" {
  bucket = aws_s3_bucket.phi_storage.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"  # Should use KMS instead
    }
  }
}

resource "aws_s3_bucket_acl" "phi_storage" {
  bucket = aws_s3_bucket.phi_storage.id
  acl    = "authenticated-read"  # Overly permissive for PHI
}

resource "aws_s3_bucket_versioning" "phi_storage" {
  bucket = aws_s3_bucket.phi_storage.id
  versioning_configuration {
    status = "Disabled"  # Should be enabled for PHI data
  }
}

resource "aws_s3_bucket_policy" "phi_storage" {
  bucket = aws_s3_bucket.phi_storage.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowPHIAccess"
        Effect    = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:*"
        }
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.phi_storage.arn}/*"
        ]
      }
    ]
  })
}