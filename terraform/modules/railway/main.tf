terraform {
  required_providers {
    railway = {
      source  = "railwayapp/railway"
      version = "~> 1.0"
    }
  }
}

provider "railway" {}

resource "railway_service" "app" {
  name        = "lechefacil-backend"
  project_id  = var.project_id
  image       = var.container_image
  environment = var.environment
}
