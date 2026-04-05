variable "primary_region" {
  type    = string
  default = "eastus"
}

variable "secondary_regions" {
  type    = list(string)
  default = ["westus2", "northeurope"]
}

variable "environment" {
  type    = string
  default = "staging"
}

variable "project_name" {
  type    = string
  default = "crucibai"
}
