resource "aws_lightsail_container_service" "app" {
  name        = "lechefacil-backend"
  power       = "micro"
  scale       = 1
  is_disabled = false
}

resource "aws_lightsail_container" "app" {
  service_name = aws_lightsail_container_service.app.name

  container {
    image = var.container_image
    name  = "web"
    ports = {
      "8000" = "HTTP"
    }
  }
}

output "endpoint" {
  value = aws_lightsail_container_service.app.url
}
