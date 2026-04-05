variable "primary_region" {
  description = "Primary deployment region (cloud-specific code, e.g. us-east-1, us-central1, eastus)"
  type        = string
  default     = "us-east-1"
}

variable "secondary_regions" {
  description = "Failover or read-replica regions (stubs only until wired to real modules)"
  type        = list(string)
  default     = ["us-west-2", "eu-west-1"]
}

variable "environment" {
  description = "Environment name (staging, prod, etc.)"
  type        = string
  default     = "staging"
}

variable "project_name" {
  description = "Prefix for resource names in examples"
  type        = string
  default     = "crucibai"
}
