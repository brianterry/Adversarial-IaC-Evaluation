# PHI Data Storage Infrastructure
# Purpose: S3 bucket for storing Protected Health Information (PHI)
# Compliance Scope: HIPAA

provider "aws" {
  region = var.aws_region
}

# Primary PHI data bucket
resource "aws_s3_bucket" "phi_storage" {
  bucket = "${var.environment}-${var.organization}-phi-data-${random_string.bucket_suffix.result}"

  tags = {
    Environment     = var.environment
    Classification  = "PHI"
    DataType        = "Healthcare"
    ComplianceScope = "HIPAA"
    Owner           = var.team_email
  }
}

# Generate random suffix for bucket name uniqueness
resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

# [V3] ACL Configuration - MISCONFIGURED FOR TRAINING
resource "aws_s3_bucket_acl" "phi_storage_acl" {
  bucket = aws_s3_bucket.phi_storage.id
  acl    = "public-read"  # VULNERABILITY: Should never be public for PHI
}

# Bucket versioning
resource "aws_s3_bucket_versioning" "phi_storage_versioning" {
  bucket = aws_s3_bucket.phi_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

# [V1] Note: Missing server-side encryption configuration
# VULNERABILITY: PHI requires explicit KMS encryption

# [V2] Note: Missing access logging configuration
# VULNERABILITY: HIPAA requires access logging

# Block public access settings
resource "aws_s3_bucket_public_access_block" "phi_storage_public_access" {
  bucket = aws_s3_bucket.phi_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}