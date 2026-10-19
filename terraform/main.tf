module "network" {
  source       = "./modules/network"
  project_name = var.project_name
  vpc_cidr     = var.vpc_cidr
  subnet_cidr  = var.subnet_cidr
  az           = var.az
}

module "compute" {
  source            = "./modules/compute"
  project_name      = var.project_name
  vpc_id            = module.network.vpc_id
  subnet_ids        = module.network.public_subnet_ids
  ami_id            = var.ami_id
  key_name          = var.key_name
  admin_cidrs       = var.admin_cidrs
  app_allowed_cidrs = coalesce(var.app_allowed_cidrs, var.admin_cidrs)
  alert_email       = var.alert_email
  instances         = var.instances
}


# Tableau de bord CloudWatch : couvre TOUTES les instances (et plus seulement les deux premières)
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6
        properties = {
          title  = "CPU (%)"
          region = var.aws_region
          period = 300
          stat   = "Average"
          metrics = [
            for name, id in module.compute.instance_ids :
            ["AWS/EC2", "CPUUtilization", "InstanceId", id, { label = name }]
          ]
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6
        properties = {
          title  = "Réseau entrant (octets)"
          region = var.aws_region
          period = 300
          stat   = "Average"
          metrics = [
            for name, id in module.compute.instance_ids :
            ["AWS/EC2", "NetworkIn", "InstanceId", id, { label = name }]
          ]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6
        properties = {
          title  = "Mémoire utilisée (%) — agent CloudWatch"
          region = var.aws_region
          period = 300
          stat   = "Average"
          metrics = [
            for name, id in module.compute.instance_ids :
            ["CWAgent", "mem_used_percent", "InstanceId", id, { label = name }]
          ]
        }
      },
      {
        type = "metric", x = 12, y = 6, width = 12, height = 6
        properties = {
          title  = "Échecs de status check"
          region = var.aws_region
          period = 60
          stat   = "Maximum"
          metrics = [
            for name, id in module.compute.instance_ids :
            ["AWS/EC2", "StatusCheckFailed", "InstanceId", id, { label = name }]
          ]
        }
      }
    ]
  })
}
