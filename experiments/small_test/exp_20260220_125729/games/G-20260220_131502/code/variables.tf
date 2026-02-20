variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-west-2"
}

variable "environment_name" {
  description = "Environment name (e.g. dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project identifier for resource naming"
  type        = string
}

variable "team_email" {
  description = "Team email for resource tagging"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where build agents will run"
  type        = string
}

variable "ci_account_id" {
  description = "AWS Account ID where CI system runs"
  type        = string
}