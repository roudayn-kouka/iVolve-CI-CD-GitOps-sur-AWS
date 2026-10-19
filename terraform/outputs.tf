output "vpc_id" {
  description = "ID du VPC"
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "IDs des sous-réseaux publics"
  value       = module.network.public_subnet_ids
}

output "security_group_ids" {
  description = "IDs des security groups (jenkins / k8s)"
  value       = module.compute.security_group_ids
}

output "instances" {
  description = "Instances : id, IP publique et privée"
  value       = module.compute.instances
}

output "instance_public_ips" {
  description = "IP publiques par nom d'instance"
  value       = { for k, v in module.compute.instances : k => v.public_ip }
}

output "sns_topic_arn" {
  description = "ARN du topic SNS des alarmes"
  value       = module.compute.sns_topic_arn
}

output "cloudwatch_dashboard_url" {
  description = "URL du tableau de bord CloudWatch"
  value       = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.main.dashboard_name}"
}
