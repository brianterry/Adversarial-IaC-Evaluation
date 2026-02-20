variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (e.g. prod, staging)"
  type        = string
  default     = "prod"
}

variable "organization" {
  description = "Organization identifier"
  type        = string
  default     = "healthcorp"
}

variable "team_email" {
  description = "Email of the team responsible for this infrastructure"
  type        = string
  default     = "phi-storage-team@healthcorp.com"
}