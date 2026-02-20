variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (e.g. prod, staging)"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where resources will be created"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for RDS cluster"
  type        = list(string)
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