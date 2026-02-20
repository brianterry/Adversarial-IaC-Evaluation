variable "aws_region" {
  type        = string
  description = "AWS region for deployment"
  default     = "us-west-2"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
  default     = "production"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID for Lambda deployment"
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnet IDs for Lambda deployment"
}

variable "db_username" {
  type        = string
  description = "Database administrator username"
  sensitive   = true
}

variable "db_password" {
  type        = string
  description = "Database administrator password"
  sensitive   = true
}