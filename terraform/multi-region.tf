# Multi-Region Deployment Configuration for CrucibAI
# Regions: us-east-1 (primary), us-west-2 (secondary), eu-west-1 (tertiary)

# Primary Region (us-east-1)
provider "aws" {
  alias  = "primary"
  region = "us-east-1"
}

# Secondary Region (us-west-2)
provider "aws" {
  alias  = "secondary"
  region = "us-west-2"
}

# Tertiary Region (eu-west-1)
provider "aws" {
  alias  = "tertiary"
  region = "eu-west-1"
}

# Route 53 Health Check for Primary Region
resource "aws_route53_health_check" "primary" {
  fqdn              = "api.crucibai.com"
  port              = 443
  type              = "HTTPS"
  failure_threshold = 3
  request_interval  = 30

  tags = {
    Name = "crucibai-primary-health-check"
  }
}

# Route 53 Health Check for Secondary Region
resource "aws_route53_health_check" "secondary" {
  fqdn              = "api-us-west.crucibai.com"
  port              = 443
  type              = "HTTPS"
  failure_threshold = 3
  request_interval  = 30

  tags = {
    Name = "crucibai-secondary-health-check"
  }
}

# Route 53 Health Check for Tertiary Region
resource "aws_route53_health_check" "tertiary" {
  fqdn              = "api-eu.crucibai.com"
  port              = 443
  type              = "HTTPS"
  failure_threshold = 3
  request_interval  = 30

  tags = {
    Name = "crucibai-tertiary-health-check"
  }
}

# Route 53 Hosted Zone
resource "aws_route53_zone" "main" {
  name = "crucibai.com"

  tags = {
    Name = "crucibai-zone"
  }
}

# Primary Region A Record (Failover - PRIMARY)
resource "aws_route53_record" "primary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.crucibai.com"
  type    = "A"

  failover_routing_policy {
    type = "PRIMARY"
  }

  alias {
    name                   = "api-primary.crucibai.com"
    zone_id                = "Z123456"  # Replace with actual ALB zone ID
    evaluate_target_health = true
  }

  set_identifier = "primary-us-east-1"
  health_check_id = aws_route53_health_check.primary.id
}

# Secondary Region A Record (Failover - SECONDARY)
resource "aws_route53_record" "secondary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.crucibai.com"
  type    = "A"

  failover_routing_policy {
    type = "SECONDARY"
  }

  alias {
    name                   = "api-secondary.crucibai.com"
    zone_id                = "Z789012"  # Replace with actual ALB zone ID
    evaluate_target_health = true
  }

  set_identifier = "secondary-us-west-2"
  health_check_id = aws_route53_health_check.secondary.id
}

# Tertiary Region A Record (Failover - SECONDARY)
resource "aws_route53_record" "tertiary" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "api.crucibai.com"
  type    = "A"

  failover_routing_policy {
    type = "SECONDARY"
  }

  alias {
    name                   = "api-tertiary.crucibai.com"
    zone_id                = "Z345678"  # Replace with actual ALB zone ID
    evaluate_target_health = true
  }

  set_identifier = "tertiary-eu-west-1"
  health_check_id = aws_route53_health_check.tertiary.id
}

# DynamoDB Global Table for Cross-Region Replication
resource "aws_dynamodb_table" "global_table" {
  name           = "crucibai-global-data"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"
  stream_specification {
    stream_view_type = "NEW_AND_OLD_IMAGES"
  }

  attribute {
    name = "id"
    type = "S"
  }

  replica {
    region_name = "us-west-2"
  }

  replica {
    region_name = "eu-west-1"
  }

  tags = {
    Name = "crucibai-global-table"
  }
}

# RDS Aurora Global Database
resource "aws_rds_global_cluster" "main" {
  global_cluster_identifier = "crucibai-global-db"
  engine                    = "aurora-postgresql"
  engine_version            = "15.2"
  database_name             = "crucibai"
}

# Primary Aurora Cluster
resource "aws_rds_cluster" "primary" {
  provider                  = aws.primary
  cluster_identifier        = "crucibai-primary"
  engine                    = aws_rds_global_cluster.main.engine
  engine_version            = aws_rds_global_cluster.main.engine_version
  database_name             = aws_rds_global_cluster.main.database_name
  master_username           = "crucibai_admin"
  master_password           = random_password.db_password.result
  global_cluster_identifier = aws_rds_global_cluster.main.id
  db_subnet_group_name      = "crucibai-db-subnet-group"
  backup_retention_period   = 30
  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = {
    Name = "crucibai-primary-cluster"
  }
}

# Primary Aurora Instance
resource "aws_rds_cluster_instance" "primary" {
  provider           = aws.primary
  cluster_identifier = aws_rds_cluster.primary.id
  instance_class     = "db.r6g.large"
  engine              = aws_rds_cluster.primary.engine
  engine_version      = aws_rds_cluster.primary.engine_version
  publicly_accessible = false

  tags = {
    Name = "crucibai-primary-instance"
  }
}

# Secondary Aurora Cluster (Read-Only)
resource "aws_rds_cluster" "secondary" {
  provider                  = aws.secondary
  cluster_identifier        = "crucibai-secondary"
  engine                    = aws_rds_global_cluster.main.engine
  engine_version            = aws_rds_global_cluster.main.engine_version
  global_cluster_identifier = aws_rds_global_cluster.main.id
  db_subnet_group_name      = "crucibai-db-subnet-group"

  depends_on = [aws_rds_cluster_instance.primary]

  tags = {
    Name = "crucibai-secondary-cluster"
  }
}

# Secondary Aurora Instance
resource "aws_rds_cluster_instance" "secondary" {
  provider           = aws.secondary
  cluster_identifier = aws_rds_cluster.secondary.id
  instance_class     = "db.r6g.large"
  engine              = aws_rds_cluster.secondary.engine
  engine_version      = aws_rds_cluster.secondary.engine_version
  publicly_accessible = false

  tags = {
    Name = "crucibai-secondary-instance"
  }
}

# Tertiary Aurora Cluster (Read-Only)
resource "aws_rds_cluster" "tertiary" {
  provider                  = aws.tertiary
  cluster_identifier        = "crucibai-tertiary"
  engine                    = aws_rds_global_cluster.main.engine
  engine_version            = aws_rds_global_cluster.main.engine_version
  global_cluster_identifier = aws_rds_global_cluster.main.id
  db_subnet_group_name      = "crucibai-db-subnet-group"

  depends_on = [aws_rds_cluster_instance.primary]

  tags = {
    Name = "crucibai-tertiary-cluster"
  }
}

# Tertiary Aurora Instance
resource "aws_rds_cluster_instance" "tertiary" {
  provider           = aws.tertiary
  cluster_identifier = aws_rds_cluster.tertiary.id
  instance_class     = "db.r6g.large"
  engine              = aws_rds_cluster.tertiary.engine
  engine_version      = aws_rds_cluster.tertiary.engine_version
  publicly_accessible = false

  tags = {
    Name = "crucibai-tertiary-instance"
  }
}

# S3 Bucket Replication (Primary to Secondary)
resource "aws_s3_bucket_replication_configuration" "primary_to_secondary" {
  provider   = aws.primary
  depends_on = [aws_s3_bucket_versioning.main]

  bucket = aws_s3_bucket.main.id

  role = aws_iam_role.s3_replication.arn

  rule {
    id     = "replicate-to-secondary"
    status = "Enabled"

    destination {
      bucket       = "arn:aws:s3:::crucibai-data-us-west-2"
      storage_class = "STANDARD_IA"

      replication_time {
        status = "Enabled"
        time {
          minutes = 15
        }
      }

      metrics {
        status = "Enabled"
        event_threshold {
          minutes = 15
        }
      }
    }
  }

  rule {
    id     = "replicate-to-tertiary"
    status = "Enabled"

    destination {
      bucket       = "arn:aws:s3:::crucibai-data-eu-west-1"
      storage_class = "STANDARD_IA"

      replication_time {
        status = "Enabled"
        time {
          minutes = 15
        }
      }
    }
  }
}

# CloudFront Distribution for Global CDN
resource "aws_cloudfront_distribution" "main" {
  enabled = true

  origin {
    domain_name = "api.crucibai.com"
    origin_id   = "crucibai-primary"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  origin {
    domain_name = "api-us-west.crucibai.com"
    origin_id   = "crucibai-secondary"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  origin {
    domain_name = "api-eu.crucibai.com"
    origin_id   = "crucibai-tertiary"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "crucibai-primary"

    forwarded_values {
      query_string = true

      cookies {
        forward = "all"
      }

      headers = ["*"]
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 3600
    max_ttl                = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name = "crucibai-cdn"
  }
}

# Lambda@Edge for Request Routing
resource "aws_lambda_function" "request_router" {
  filename      = "lambda_request_router.zip"
  function_name = "crucibai-request-router"
  role          = aws_iam_role.lambda_edge.arn
  handler       = "index.handler"
  runtime       = "python3.11"

  tags = {
    Name = "crucibai-request-router"
  }
}

# Random password for database
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# IAM Role for S3 Replication
resource "aws_iam_role" "s3_replication" {
  name = "crucibai-s3-replication-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "s3.amazonaws.com"
      }
    }]
  })
}

# IAM Role for Lambda@Edge
resource "aws_iam_role" "lambda_edge" {
  name = "crucibai-lambda-edge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

# S3 Bucket for Multi-Region Data
resource "aws_s3_bucket" "main" {
  provider = aws.primary
  bucket   = "crucibai-data-primary"

  tags = {
    Name = "crucibai-data-primary"
  }
}

resource "aws_s3_bucket_versioning" "main" {
  provider = aws.primary
  bucket   = aws_s3_bucket.main.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Outputs
output "primary_endpoint" {
  value       = "api.crucibai.com"
  description = "Primary region endpoint"
}

output "secondary_endpoint" {
  value       = "api-us-west.crucibai.com"
  description = "Secondary region endpoint"
}

output "tertiary_endpoint" {
  value       = "api-eu.crucibai.com"
  description = "Tertiary region endpoint"
}

output "cloudfront_domain" {
  value       = aws_cloudfront_distribution.main.domain_name
  description = "CloudFront CDN domain"
}

output "rto_minutes" {
  value       = 5
  description = "Recovery Time Objective in minutes"
}

output "rpo_minutes" {
  value       = 1
  description = "Recovery Point Objective in minutes"
}
