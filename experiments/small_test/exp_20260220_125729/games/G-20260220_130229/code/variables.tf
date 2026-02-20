variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "project_prefix" {
  description = "Prefix for resource naming"
  type        = string
  default     = "company"
}

variable "project_name" {
  description = "Project name for tagging"
  type        = string
  default     = "main-pipeline"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}