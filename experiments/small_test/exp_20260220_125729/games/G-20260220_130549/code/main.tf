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

# PHI Data Storage Bucket - Intentionally Insecure
resource "aws_s3_bucket" "medical_records" {
  bucket = "healthcare-phi-data-${var.environment}"
  
  tags = {
    Name        = "Medical Records Bucket"
    Environment = var.environment
    Compliance  = "HIPAA"
    Department  = "Healthcare"
  }
}

# Public Access Block - Deliberately Weak
resource "aws_s3_bucket_public_access_block" "medical_records" {
  bucket = aws_s3_bucket.medical_records.id

  block_public_acls       = false  # VULNERABILITY: Allows public ACLs
  block_public_policy     = false  # VULNERABILITY: Allows public policies
  ignore_public_acls      = false  # VULNERABILITY: Ignores public ACL restrictions
  restrict_public_buckets = false  # VULNERABILITY: Allows public bucket access
}

# Database for Medical Records - Unencrypted
resource "aws_db_instance" "medical_database" {
  identifier           = "medical-records-db-${var.environment}"
  engine               = "postgres"
  engine_version       = "13.7"
  instance_class       = "db.t3.medium"
  allocated_storage    = 20
  username             = var.db_username

  # VULNERABILITY: No storage encryption
  # storage_encrypted is intentionally omitted

  vpc_security_group_ids = [aws_security_group.database.id]

  tags = {
    Name        = "Medical Records Database"
    Environment = var.environment
    Compliance  = "HIPAA"
  }
}

# Security Group - Overly Permissive
resource "aws_security_group" "database" {
  name        = "medical-database-sg"
  description = "Security group for medical records database"

  # VULNERABILITY: Open ingress rule
  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]  # Allows access from anywhere
  }

  tags = {
    Name        = "Medical Database Security Group"
    Environment = var.environment
  }
}

# Optional: Simulating a minimal logging configuration
resource "aws_cloudwatch_log_group" "database_logs" {
  name              = "/aws/rds/instance/${aws_db_instance.medical_database.identifier}/general"
  retention_in_days = 14
}