# AWS multi-region STUB — add VPC, subnets, RDS Global Cluster, Route53 failover, ECR per region.
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.primary_region
}

data "aws_region" "primary" {}

locals {
  secondary = var.secondary_regions
}

# Example: one alias per fixed secondary region (expand with module for_each when ready)
provider "aws" {
  alias  = "secondary_a"
  region = length(local.secondary) > 0 ? local.secondary[0] : var.primary_region
}

provider "aws" {
  alias  = "secondary_b"
  region = length(local.secondary) > 1 ? local.secondary[1] : var.primary_region
}

output "primary_region" {
  value       = data.aws_region.primary.name
  description = "Resolved primary region"
}

output "secondary_regions" {
  value       = local.secondary
  description = "Configured secondary regions (stubs — no RDS created here)"
}

output "environment" {
  value = var.environment
}

output "stub_note" {
  value = "No Aurora/global DB in this stub — add aws_rds_global_cluster + regional clusters, networking, and secrets management before apply."
}
