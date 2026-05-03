terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    bucket         = "crucibai-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CrucibAI"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# S3 bucket for backups
resource "aws_s3_bucket" "backups" {
  bucket = "crucibai-backups-${var.environment}"
}

resource "aws_s3_bucket_versioning" "backups" {
  bucket = aws_s3_bucket.backups.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "backups" {
  bucket = aws_s3_bucket.backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "backups" {
  bucket = aws_s3_bucket.backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 bucket for application logs
resource "aws_s3_bucket" "logs" {
  bucket = "crucibai-logs-${var.environment}"
}

resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "delete-old-logs"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

# IAM role for backup operations
resource "aws_iam_role" "backup_role" {
  name = "crucibai-backup-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "backup_policy" {
  name = "crucibai-backup-policy"
  role = aws_iam_role.backup_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.backups.arn,
          "${aws_s3_bucket.backups.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}

# Secrets Manager for sensitive data
resource "aws_secretsmanager_secret" "database_url" {
  name                    = "crucibai/database-url/${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name                    = "crucibai/jwt-secret/${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "paypal_client_id" {
  name                    = "crucibai/paypal-client-id/${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "paypal_client_secret" {
  name                    = "crucibai/paypal-client-secret/${var.environment}"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret" "sentry_dsn" {
  name                    = "crucibai/sentry-dsn/${var.environment}"
  recovery_window_in_days = 7
}

# CloudWatch Log Group for application logs
resource "aws_cloudwatch_log_group" "app_logs" {
  name              = "/crucibai/app/${var.environment}"
  retention_in_days = 30

  tags = {
    Name = "crucibai-app-logs"
  }
}

resource "aws_cloudwatch_log_group" "agent_logs" {
  name              = "/crucibai/agents/${var.environment}"
  retention_in_days = 30

  tags = {
    Name = "crucibai-agent-logs"
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "crucibai-high-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ErrorRate"
  namespace           = "CrucibAI"
  period              = 300
  statistic           = "Average"
  threshold           = 5.0
  alarm_description   = "Alert when error rate exceeds 5%"
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "crucibai-high-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Latency"
  namespace           = "CrucibAI"
  period              = 300
  statistic           = "Average"
  threshold           = 500
  alarm_description   = "Alert when p95 latency exceeds 500ms"
  treat_missing_data  = "notBreaching"
}

# DynamoDB table for Terraform state locking
resource "aws_dynamodb_table" "terraform_locks" {
  name           = "terraform-locks"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "terraform-locks"
  }
}

# S3 bucket for Terraform state
resource "aws_s3_bucket" "terraform_state" {
  bucket = "crucibai-terraform-state-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "aws_caller_identity" "current" {}

# Outputs
output "backup_bucket_name" {
  value       = aws_s3_bucket.backups.id
  description = "Name of the S3 bucket for backups"
}

output "logs_bucket_name" {
  value       = aws_s3_bucket.logs.id
  description = "Name of the S3 bucket for logs"
}

output "backup_role_arn" {
  value       = aws_iam_role.backup_role.arn
  description = "ARN of the backup IAM role"
}

output "app_log_group_name" {
  value       = aws_cloudwatch_log_group.app_logs.name
  description = "Name of the application log group"
}

output "agent_log_group_name" {
  value       = aws_cloudwatch_log_group.agent_logs.name
  description = "Name of the agent log group"
}
