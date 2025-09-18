output "deployment_endpoint" {
  description = "Endpoint of the deployed service"
  value       = module.lightsail.endpoint
  sensitive   = false
}
