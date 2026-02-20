variable "aws_region" {
  description = "AWS region for PHI storage infrastructure"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Project identifier"
  type        = string
  default     = "healthcare"
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "Healthcare Platform"
    Owner       = "Platform Team"
    Compliance  = "HIPAA"
    DataType    = "PHI"
    CostCenter  = "12345"
  }
}