output "endpoint" {
  description = "Lightsail public endpoint"
  value       = aws_lightsail_container_service.app.url
}
