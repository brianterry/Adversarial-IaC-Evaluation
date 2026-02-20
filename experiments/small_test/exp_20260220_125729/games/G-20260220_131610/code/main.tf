```hcl
provider "aws" {
  region = var.region
}

# Healthcare PHI Data Storage Bucket
resource "aws_s3_bucket" "medical_records" {
  bucket = "patient-records-${var.environment}"

  tags = {
    Name        = "Medical Records Storage"
    Environment = var.environment
    Department  = "Healthcare IT"
    Sensitivity = "PHI"
    ManagedBy   = "Terraform"
  }
}

# Public Access Configuration (INTENTIONALLY INSECURE)
resource "aws_s3_bucket_public_access_block" "medical_records" {
  bucket = aws_s3_bucket.medical_records.id

  # VULNERABILITY: Completely disabling public access protections
  block_public_acls       = false
  block_public_policy    = false
  ignore_public_acls     = false
  restrict_public_buckets = false
}

# Access Control List (Minimal Configuration)
resource "aws_s3_bucket_ownership_controls" "medical_records" {
  bucket = aws_s3_bucket.medical_records.id

  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Optional: KMS Key for potential encryption (not applied)
resource "aws_kms_key" "medical_records_key" {
  description             = "KMS key for medical records bucket"
  deletion_window_in_days = 10
  enable_key_rotation     = true
}

# Optional: IAM Policy for bucket access
resource "aws_iam_policy" "medical_records_access" {
  name        = "medical-records-access-policy"
  path        = "/"
  description = "Policy for accessing medical records bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Effect   = "Allow"
        Resource = "${aws_s3_bucket.medical_records.arn}/*"
      }
    ]
  })
}
```