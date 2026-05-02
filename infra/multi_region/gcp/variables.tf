variable "primary_region" {
  type    = string
  default = "us-central1"
}

variable "secondary_regions" {
  type    = list(string)
  default = ["us-east1", "europe-west1"]
}

variable "environment" {
  type    = string
  default = "staging"
}

variable "project_name" {
  type    = string
  default = "crucibai"
}

variable "network_id" {
  description = "VPC self_link or network id for private IP Cloud SQL (fill when wiring)"
  type        = string
  default     = ""
}
