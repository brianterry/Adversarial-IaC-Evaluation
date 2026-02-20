variable "aws_region" {
  description = "AWS region for resource deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "prod"
}

variable "organization" {
  description = "Organization name for resource naming"
  type        = string
  default     = "healthcorp"
}

variable "team_email" {
  description = "Email address of the team responsible for this resource"
  type        = string
  default     = "healthcare-data@example.com"
}

variable "cost_center" {
  description = "Cost center for billing purposes"
  type        = string
  default     = "HC-DATA-01"
}