locals {
  names = sort(keys(var.instances))
}

# ---------- AMI : Ubuntu 22.04 LTS officielle (Canonical) ----------
data "aws_ami" "ubuntu" {
  count       = var.ami_id == null ? 1 : 0
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

locals {
  ami_id = coalesce(var.ami_id, try(data.aws_ami.ubuntu[0].id, null))
}

# ---------- Security groups : un par rôle, aucune ouverture sur 0.0.0.0/0 en entrée ----------
resource "aws_security_group" "jenkins" {
  name        = "${var.project_name}-jenkins-sg"
  description = "Jenkins master/agent"
  vpc_id      = var.vpc_id
  tags        = { Name = "${var.project_name}-jenkins-sg" }
}

resource "aws_security_group" "k8s" {
  name        = "${var.project_name}-k8s-sg"
  description = "Noeuds Kubernetes (kubeadm)"
  vpc_id      = var.vpc_id
  tags        = { Name = "${var.project_name}-k8s-sg" }
}

# --- Jenkins ---
resource "aws_vpc_security_group_ingress_rule" "jenkins_ssh" {
  for_each          = toset(var.admin_cidrs)
  security_group_id = aws_security_group.jenkins.id
  description       = "SSH admin"
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_ingress_rule" "jenkins_ui" {
  for_each          = toset(var.admin_cidrs)
  security_group_id = aws_security_group.jenkins.id
  description       = "Interface Jenkins"
  ip_protocol       = "tcp"
  from_port         = 8080
  to_port           = 8080
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_ingress_rule" "jenkins_self" {
  security_group_id            = aws_security_group.jenkins.id
  description                  = "Master <-> agent (SSH, JNLP) à l'intérieur du groupe"
  ip_protocol                  = "-1"
  referenced_security_group_id = aws_security_group.jenkins.id
}

# --- Kubernetes ---
resource "aws_vpc_security_group_ingress_rule" "k8s_ssh" {
  for_each          = toset(var.admin_cidrs)
  security_group_id = aws_security_group.k8s.id
  description       = "SSH admin"
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_ingress_rule" "k8s_api" {
  for_each          = toset(var.admin_cidrs)
  security_group_id = aws_security_group.k8s.id
  description       = "API Kubernetes (kubectl depuis l'admin)"
  ip_protocol       = "tcp"
  from_port         = 6443
  to_port           = 6443
  cidr_ipv4         = each.value
}

resource "aws_vpc_security_group_ingress_rule" "k8s_self" {
  security_group_id            = aws_security_group.k8s.id
  description                  = "Trafic inter-noeuds (API 6443, kubelet 10250, VXLAN Flannel 8472/udp, pods...)"
  ip_protocol                  = "-1"
  referenced_security_group_id = aws_security_group.k8s.id
}

resource "aws_vpc_security_group_ingress_rule" "k8s_nodeport" {
  for_each          = toset(var.app_allowed_cidrs)
  security_group_id = aws_security_group.k8s.id
  description       = "Application : NodePorts"
  ip_protocol       = "tcp"
  from_port         = 30000
  to_port           = 32767
  cidr_ipv4         = each.value
}

# Sortie ouverte (apt, DockerHub, GitHub, registres) — à restreindre via proxy/endpoints en production
resource "aws_vpc_security_group_egress_rule" "jenkins_all" {
  security_group_id = aws_security_group.jenkins.id
  description       = "Sortie internet"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_egress_rule" "k8s_all" {
  security_group_id = aws_security_group.k8s.id
  description       = "Sortie internet"
  ip_protocol       = "-1"
  cidr_ipv4         = "0.0.0.0/0"
}

# ---------- IAM : SSM (accès sans SSH possible) + agent CloudWatch ----------
data "aws_iam_policy_document" "ec2_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ec2" {
  name               = "${var.project_name}-ec2-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume.json
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.ec2.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2.name
}

# ---------- Instances ----------
resource "aws_instance" "app" {
  for_each = var.instances

  ami                         = local.ami_id
  instance_type               = each.value.instance_type
  key_name                    = var.key_name
  subnet_id                   = var.subnet_ids[index(local.names, each.key) % length(var.subnet_ids)]
  vpc_security_group_ids      = [each.value.role == "jenkins" ? aws_security_group.jenkins.id : aws_security_group.k8s.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2.name
  associate_public_ip_address = true
  ebs_optimized               = true
  monitoring                  = false

  # IMDSv2 obligatoire (protège contre le vol de credentials via SSRF)
  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
  }

  root_block_device {
    volume_size           = each.value.volume_size
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  tags = {
    Name = each.key
    Role = each.value.role
  }

  lifecycle {
    # Une nouvelle AMI Ubuntu ne doit pas recréer des machines déjà configurées
    ignore_changes = [ami]
  }
}

# ---------- Alertes ----------
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email == "" ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "cpu" {
  for_each            = aws_instance.app
  alarm_name          = "${var.project_name}-${each.key}-cpu-high"
  alarm_description   = "CPU >= 80 % pendant 10 min sur ${each.key}"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  dimensions          = { InstanceId = each.value.id }
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "status_check" {
  for_each            = aws_instance.app
  alarm_name          = "${var.project_name}-${each.key}-status-check-failed"
  alarm_description   = "Échec du status check EC2 sur ${each.key}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  dimensions          = { InstanceId = each.value.id }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "memory" {
  for_each            = aws_instance.app
  alarm_name          = "${var.project_name}-${each.key}-memory-high"
  alarm_description   = "Mémoire >= 85 % sur ${each.key} (nécessite l'agent CloudWatch installé par Ansible)"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  metric_name         = "mem_used_percent"
  namespace           = "CWAgent"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  dimensions          = { InstanceId = each.value.id }
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
