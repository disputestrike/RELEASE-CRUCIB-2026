"""
Multi-region / multi-cloud Terraform **sketches** — educational stubs, not production modules.
Emitted when goals mention Terraform plus AWS/GCP/Azure and/or multi-region / DR patterns.
"""
from __future__ import annotations

import re
from typing import Any, Dict


def _g(job_or_goal: Any) -> str:
    if isinstance(job_or_goal, str):
        return (job_or_goal or "").lower()
    return (job_or_goal.get("goal") or "").lower()


def multiregion_terraform_intent(job_or_goal: Dict[str, Any] | str) -> bool:
    g = _g(job_or_goal)
    multiregion = bool(
        re.search(
            r"\b(multi[\s-]?region|multi region|cross[\s-]?region|active[\s-]?active|"
            r"geo[\s-]?redundan|global load|route53 health|failover region)\b",
            g,
        )
    )
    cloud = bool(re.search(r"\b(aws|amazon|gcp|google cloud|azure|eks|gke|aks)\b", g))
    terraform = "terraform" in g
    return multiregion or (terraform and cloud)


def build_multiregion_terraform_readme(goal_excerpt: str) -> str:
    ex = ((goal_excerpt or "").strip()[:400] or "(no goal text)").replace("\n", " ")
    return f"""# Multi-region Terraform sketch

**Auto-Runner** generated minimal provider stubs under `terraform/modules/*` and a sample root in
`terraform/multiregion_sketch/`. This is **not** a complete VPC, IAM, or data-replication design.

## Goal excerpt

> {ex}

## Layout

```
infra/multi_region/   # Repo-root stubs: aws/, gcp/, azure/ + shared variables.tf
terraform/
  multiregion_sketch/
    main.tf       # Example module calls (primary + optional secondary region variables)
    variables.tf
    outputs.tf
    README.md     # This file
  modules/
    aws_region_stub/
    gcp_region_stub/
    azure_region_stub/
```

## Next steps (you own these)

1. **State** — remote backend (S3 + DynamoDB, GCS + lock, Azure Storage).
2. **Networking** — VPC/VNet per region, peering or transit, private endpoints for data stores.
3. **Data** — RDS / Cloud SQL / Cosmos replication, RPO/RTO targets, backup policies.
4. **Traffic** — DNS (Route53/Cloud DNS/Azure DNS), health checks, weighted or failover routing.
5. **Secrets** — never commit credentials; use CI OIDC + provider secret stores.

Run `terraform fmt` and `terraform validate` after filling in provider configuration.

_Schema: crucibai.multiregion_terraform_sketch/v1_
"""


def tf_aws_region_stub_main() -> str:
    return '''# AWS region stub — add VPC, subnets, TGW, and RDS cross-region read replicas as needed.
terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "region" {
  type        = string
  description = "AWS region name, e.g. us-east-1"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Deployment label for tags"
}

provider "aws" {
  region = var.region
}

# Example tag baseline (uncomment to apply)
# resource "aws_default_vpc" "this" {
#   tags = { Name = "default-${var.environment}", ManagedBy = "terraform-stub" }
# }

output "region" {
  value       = var.region
  description = "Configured AWS region"
}
'''


def tf_gcp_region_stub_main() -> str:
    return '''# GCP region stub — add VPC, subnets, Cloud SQL HA, and multi-region GCS as needed.
terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "region" {
  type        = string
  description = "GCP region, e.g. us-central1"
}

variable "project_id" {
  type        = string
  description = "GCP project ID"
}

variable "environment" {
  type        = string
  default     = "dev"
}

provider "google" {
  region  = var.region
  project = var.project_id
}

output "region" {
  value = var.region
}
'''


def tf_azure_region_stub_main() -> str:
    return '''# Azure region stub — add VNet, peering, and geo-redundant storage / Cosmos as needed.
terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }
}

variable "location" {
  type        = string
  description = "Azure region, e.g. eastus"
}

variable "environment" {
  type        = string
  default     = "dev"
}

provider "azurerm" {
  features {}
}

output "location" {
  value = var.location
}
'''


def tf_multiregion_root_main() -> str:
    return '''# Example root — wire credentials via env vars or CI OIDC before apply.
# terraform init
# terraform plan -var="aws_primary_region=us-east-1" -var="aws_secondary_region=us-west-2"

module "aws_primary" {
  source      = "../modules/aws_region_stub"
  region      = var.aws_primary_region
  environment = var.environment
}

module "aws_secondary" {
  count       = var.enable_secondary_aws ? 1 : 0
  source      = "../modules/aws_region_stub"
  region      = var.aws_secondary_region
  environment = var.environment
}

# Uncomment when targeting GCP / Azure in the same blueprint:
# module "gcp_primary" {
#   source     = "../modules/gcp_region_stub"
#   region     = var.gcp_region
#   project_id = var.gcp_project_id
#   environment = var.environment
# }
#
# module "azure_primary" {
#   source      = "../modules/azure_region_stub"
#   location    = var.azure_location
#   environment = var.environment
# }

output "aws_primary_region" {
  value = module.aws_primary.region
}
'''


def tf_multiregion_variables_tf() -> str:
    return '''variable "environment" {
  type    = string
  default = "dev"
}

variable "aws_primary_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_secondary_region" {
  type    = string
  default = "us-west-2"
}

variable "enable_secondary_aws" {
  type    = bool
  default = false
}

variable "gcp_region" {
  type    = string
  default = "us-central1"
}

variable "gcp_project_id" {
  type    = string
  default = ""
}

variable "azure_location" {
  type    = string
  default = "eastus"
}
'''


def tf_multiregion_outputs_tf() -> str:
    return '''output "stub_note" {
  value       = "Terraform sketch only — add networking, data replication, and DNS before production."
  description = "Reminder"
}
'''
