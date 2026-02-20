```hcl
# Healthcare PHI Data Storage Bucket
# Note: This is a TRAINING EXAMPLE with intentional security misconfigurations

provider "aws" {
  region = var.aws_region
}

resource "aws_s3_bucket" "medical_records" {
  bucket = "healthcare-phi-data-${var.environment}"

  tags = {
    Name        = "Medical Records Storage"
    Environment = var.environment
    Sensitivity = "PHI"
    ManagedBy   = "Terraform"
  }

  # VULNERABILITY V3: No logging configuration
}

# VULNERABILITY V2: Permissive Public Access Block
resource "aws_s3_bucket_public_access_block" "medical_records" {
  bucket = aws_s3_bucket.medical_records.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# VULNERABILITY V1: No explicit encryption configuration
# This leaves the bucket unencrypted by default

# Optional logging target bucket (not configured in this example)
resource "aws_s3_bucket" "log_bucket" {
  bucket = "healthcare-phi-logs-${var.environment}"

  tags = {
    Name        = "Access Logs Bucket"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Additional resource to simulate a more complex setup
resource "aws_s3_bucket_versioning" "medical_records" {
  bucket = aws_s3_bucket.medical_records.id
  versioning_configuration {
    status = "Enabled"
  }
}
```