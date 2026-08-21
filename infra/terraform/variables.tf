variable "aws_profile" {
  description = "AWS CLI profile to use for every resource in this stack."
  type        = string
  default     = "aayush-gift"
}

variable "aws_region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Short project name used to prefix/name resources."
  type        = string
  default     = "austial"
}

variable "environment" {
  description = "Deployment environment tag."
  type        = string
  default     = "demo"
}

variable "instance_type" {
  description = "EC2 instance type for the backend host. Kept at t3.micro (free-tier eligible) per cost constraints."
  type        = string
  default     = "t3.micro"
}

variable "db_instance_class" {
  description = "RDS instance class. Kept at db.t3.micro per cost constraints."
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS storage size in GB."
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Initial database name."
  type        = string
  default     = "swadely"
}

variable "db_username" {
  description = "Master username for RDS."
  type        = string
  default     = "swadely"
}

variable "db_password" {
  description = "Master password for RDS. Passed in via TF_VAR_db_password / terraform.tfvars, not committed."
  type        = string
  sensitive   = true
}

variable "app_port" {
  description = "Port the backend container listens on."
  type        = number
  default     = 8000
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository for the backend image."
  type        = string
  default     = "austial-backend"
}

variable "container_image_tag" {
  description = "Tag of the backend image to run. Updated after the first `docker push`; user-data pulls this tag on boot."
  type        = string
  default     = "latest"
}

variable "api_key" {
  description = "Value for the app's API_KEY env var (used by the protected health route)."
  type        = string
  sensitive   = true
  default     = "changeme"
}
