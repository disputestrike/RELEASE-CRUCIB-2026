variable "primary_region" {
  type    = string
  default = "us-east-1"
}

variable "secondary_regions" {
  type    = list(string)
  default = ["us-west-2", "eu-west-1"]
}

variable "environment" {
  type    = string
  default = "staging"
}

variable "project_name" {
  type    = string
  default = "crucibai"
}
