# Healthcare PHI Data Storage Solution
# Purpose: Store Protected Health Information (PHI) with appropriate security controls
# Environment: Production
# Last Updated: 2024

provider "aws" {
  region = var.aws_region
}

# Primary PHI data storage bucket
resource "aws_s3_bucket" "phi_storage" {
  bucket = "${var.environment}-${var.organization}-phi-data-${random_id.bucket_suffix.hex}"

  tags = {
    Environment     = var.environment
    Classification  = "PHI"
    DataType        = "Healthcare"
    Compliance      = "HIPAA"
    Owner           = var.team_email
    CostCenter     = var.cost_center
  }
}

# Generate unique suffix for bucket name
resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Bucket versioning configuration
resource "aws_s3_bucket_versioning" "phi_versioning" {
  bucket = aws_s3_bucket.phi_storage.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ACL Configuration - Intentionally misconfigured for training
resource "aws_s3_bucket_acl" "phi_bucket_acl" {
  bucket = aws_s3_bucket.phi_storage.id
  acl    = "public-read"  # V3: Dangerous misconfiguration
}

# Public access block configuration
resource "aws_s3_bucket_public_access_block" "phi_public_access" {
  bucket = aws_s3_bucket.phi_storage.id
  
  # Partially configured, creating a false sense of security
  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = false
}

# Note: Intentionally missing server-side encryption configuration (V1)
# Note: Intentionally missing access logging configuration (V2)