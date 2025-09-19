variable "environment" {
  description = "Deployment environment name"
  type        = string
}

variable "railway_project_id" {
  description = "Railway project identifier"
  type        = string
  default     = ""
}

variable "container_image" {
  description = "OCI image to deploy (for example ghcr.io/owner/repo:tag)"
  type        = string
}
