```hcl
# Healthcare Data Storage Infrastructure
# Simulating a rapid prototype deployment for medical records management

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

# PHI Data Storage Bucket
resource "aws_s3_bucket" "medical_records" {
  bucket        = "healthcare-phi-storage-${var.environment}"
  force_destroy = true  # Dangerous for production, but common in prototypes

  tags = {
    Name        = "Medical Records Storage"
    Environment = var.environment
    Sensitivity = "PHI"
    Project     = "HealthTrack Prototype"
  }
}

# Public Access Configuration (Intentionally Weak)
resource "aws_s3_bucket_public_access_block" "medical_records" {
  bucket = aws_s3_bucket.medical_records.id

  block_public_acls       = false  # VULNERABILITY: Allows public ACLs
  block_public_policy     = false  # VULNERABILITY: Allows public policies
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Backend Services Security Group (Overly Permissive)
resource "aws_security_group" "backend_services" {
  name        = "healthcare-backend-sg"
  description = "Security group for healthcare backend services"

  # VULNERABILITY: Wide-open ingress rules
  ingress {
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
    Name        = "Healthcare Backend SG"
    Environment = var.environment
  }
}

# Database for Patient Records (Unencrypted)
resource "aws_db_instance" "patient_records" {
  identifier           = "healthcare-patient-db-${var.environment}"
  engine               = "postgres"
  engine_version       = "13.7"
  instance_class       = "db.t3.medium"
  allocated_storage    = 20
  storage_type         = "gp2"
  storage_encrypted    = false  # VULNERABILITY: Unencrypted storage

  username = var.db_username
  password = var.db_password

  backup_retention_period = 7
  skip_final_snapshot     = true

  tags = {
    Name        = "Patient Records Database"
    Environment = var.environment
    Sensitivity = "PHI"
  }
}

# Simulated Application Servers
resource "aws_instance" "app_servers" {
  count         = 2
  ami           = var.app_ami
  instance_type = "t3.medium"

  vpc_security_group_ids = [aws_security_group.backend_services.id]

  tags = {
    Name        = "HealthTrack-AppServer-${count.index + 1}"
    Environment = var.environment
    Role        = "Backend"
  }
}
```