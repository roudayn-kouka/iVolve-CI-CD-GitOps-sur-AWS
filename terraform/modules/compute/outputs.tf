output "security_group_ids" {
  description = "IDs des security groups par rôle"
  value = {
    jenkins = aws_security_group.jenkins.id
    k8s     = aws_security_group.k8s.id
  }
}

output "instance_ids" {
  description = "IDs des instances, par nom"
  value       = { for k, v in aws_instance.app : k => v.id }
}

output "instances" {
  description = "Détails des instances, par nom"
  value = {
    for k, v in aws_instance.app : k => {
      id         = v.id
      public_ip  = v.public_ip
      private_ip = v.private_ip
      role       = var.instances[k].role
    }
  }
}

output "sns_topic_arn" {
  description = "ARN du topic SNS"
  value       = aws_sns_topic.alerts.arn
}
