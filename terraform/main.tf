module "railway" {
  source          = "./modules/railway"
  project_id      = var.railway_project_id
  container_image = var.container_image
  environment     = var.environment
}
