output "backend_public_ip" {
  description = "Elastic IP attached to the backend EC2 instance."
  value       = aws_eip.backend.public_ip
}

output "backend_health_url" {
  description = "Backend health-check URL."
  value       = "http://${aws_eip.backend.public_ip}:${var.app_port}/health"
}

output "backend_instance_id" {
  description = "EC2 instance ID (for SSM Session Manager access)."
  value       = aws_instance.backend.id
}

output "rds_endpoint" {
  description = "RDS Postgres endpoint (host:port), reachable only from the backend EC2 SG."
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "RDS Postgres hostname."
  value       = aws_db_instance.main.address
}

output "ecr_repository_url" {
  description = "ECR repository URL to push the backend image to."
  value       = aws_ecr_repository.backend.repository_url
}

output "s3_website_endpoint" {
  description = "S3 static website endpoint for the Angular frontend."
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for the Angular frontend build output."
  value       = aws_s3_bucket.frontend.id
}

output "documents_s3_bucket_name" {
  description = "Private S3 bucket name for KYC/disclosure documents (DOCUMENTS_S3_BUCKET env var)."
  value       = aws_s3_bucket.documents.id
}
