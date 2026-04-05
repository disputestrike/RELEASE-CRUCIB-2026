# GCP multi-region STUB — add Cloud SQL HA primary + cross-region read replicas, private VPC, IAM.
terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  region = var.primary_region
}

output "primary_region" {
  value = var.primary_region
}

output "secondary_regions" {
  value = var.secondary_regions
}

output "environment" {
  value = var.environment
}

output "stub_note" {
  value = "No Cloud SQL instance created — configure google provider project, network_id, and replica blocks before apply."
}
