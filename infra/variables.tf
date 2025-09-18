variable "environment" {
  description = "Deployment environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region for Lightsail deployments"
  type        = string
  default     = "us-east-1"
}

variable "railway_project_id" {
  description = "Railway project identifier"
  type        = string
  default     = ""
}

variable "container_image" {
  description = "OCI image to deploy"
  type        = string
}
