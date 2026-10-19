variable "aws_region" {
  description = "Région AWS"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Nom du projet (préfixe des ressources et tag Project)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR du VPC"
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR des sous-réseaux publics (un par AZ)"
  type        = list(string)
}

variable "az" {
  description = "Zones de disponibilité (même longueur que subnet_cidr)"
  type        = list(string)

  validation {
    condition     = length(var.az) > 0
    error_message = "Au moins une zone de disponibilité est requise."
  }
}

variable "key_name" {
  description = "Nom de la paire de clés SSH EC2 existante"
  type        = string
}

variable "ami_id" {
  description = "AMI à utiliser. null = dernière Ubuntu 22.04 LTS officielle (Canonical)"
  type        = string
  default     = null
}

variable "admin_cidrs" {
  description = "CIDR autorisés pour SSH, Jenkins (8080) et l'API Kubernetes (6443)"
  type        = list(string)

  validation {
    condition     = length(var.admin_cidrs) > 0 && !contains(var.admin_cidrs, "0.0.0.0/0")
    error_message = "admin_cidrs doit contenir au moins un CIDR et ne doit pas ouvrir 0.0.0.0/0."
  }
}

variable "app_allowed_cidrs" {
  description = "CIDR autorisés à joindre l'application (NodePorts 30000-32767). null = admin_cidrs"
  type        = list(string)
  default     = null
}

variable "alert_email" {
  description = "E-mail abonné au topic SNS des alarmes (vide = aucun abonnement)"
  type        = string
  default     = ""
}

variable "instances" {
  description = "Machines à créer : role = jenkins | k8s"
  type = map(object({
    role          = string
    instance_type = string
    volume_size   = number
  }))
  default = {
    jenkins-master = { role = "jenkins", instance_type = "t3.medium", volume_size = 30 }
    jenkins-slave  = { role = "jenkins", instance_type = "t3.medium", volume_size = 40 }
    kubemaster     = { role = "k8s", instance_type = "t3.medium", volume_size = 30 }
    kubenode1      = { role = "k8s", instance_type = "t3.medium", volume_size = 30 }
  }

  validation {
    condition     = alltrue([for i in values(var.instances) : contains(["jenkins", "k8s"], i.role)])
    error_message = "role doit valoir \"jenkins\" ou \"k8s\"."
  }
}
