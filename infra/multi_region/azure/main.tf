# Azure multi-region STUB — add paired regions, Front Door / Traffic Manager, geo-redundant storage.
terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
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
  value = "No resources created — set subscription_id, resource group modules, and networking before apply."
}
