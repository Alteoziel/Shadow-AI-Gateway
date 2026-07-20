# Minimal Terraform stub — Layer E (IaC learning surface).
# Phase 4 human checkpoint expands this. CI runs Checkov against this directory.

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

variable "aws_region" {
  type        = string
  description = "AWS region for the private gateway deployment"
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Name prefix for gateway resources"
  default     = "shadow-ai-gateway"
}

# Placeholder: Phase 4 human checkpoint defines VPC/ECS/ALB resources here.
# Kept intentionally minimal so Checkov has a valid root module to scan.
resource "aws_cloudwatch_log_group" "gateway" {
  name              = "/${var.project_name}/gateway"
  retention_in_days = 365
}
