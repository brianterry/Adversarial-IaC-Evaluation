variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "db_username" {
  description = "Master username for RDS cluster"
  type        = string
  sensitive   = true
}

variable "db_password" {
  description = "Master password for RDS cluster"
  type        = string
  sensitive   = true
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = {
    Environment = "prod"
    Project     = "payment-processing"
    Owner       = "financial-systems"
    ManagedBy   = "terraform"
  }
}