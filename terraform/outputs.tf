output "deployment_endpoint" {
  description = "Endpoint of the deployed service"
  value       = module.railway.endpoint
  sensitive   = false
}
