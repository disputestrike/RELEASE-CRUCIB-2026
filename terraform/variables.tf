variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

variable "enable_encryption" {
  description = "Enable encryption for all resources"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "primary_alias_dns_name" {
  description = "DNS name for the primary regional load balancer or API endpoint"
  type        = string
}

variable "primary_alias_zone_id" {
  description = "Route53 hosted zone ID for the primary regional alias target"
  type        = string
}

variable "secondary_alias_dns_name" {
  description = "DNS name for the secondary regional load balancer or API endpoint"
  type        = string
}

variable "secondary_alias_zone_id" {
  description = "Route53 hosted zone ID for the secondary regional alias target"
  type        = string
}

variable "tertiary_alias_dns_name" {
  description = "DNS name for the tertiary regional load balancer or API endpoint"
  type        = string
}

variable "tertiary_alias_zone_id" {
  description = "Route53 hosted zone ID for the tertiary regional alias target"
  type        = string
}
