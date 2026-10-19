variable "project_name" {
  description = "Nom du projet"
  type        = string
}

variable "vpc_id" {
  description = "ID du VPC"
  type        = string
}

variable "subnet_ids" {
  description = "Sous-réseaux où répartir les instances"
  type        = list(string)
}

variable "ami_id" {
  description = "AMI (null = dernière Ubuntu 22.04 LTS Canonical)"
  type        = string
  default     = null
}

variable "key_name" {
  description = "Paire de clés SSH"
  type        = string
}

variable "admin_cidrs" {
  description = "CIDR d'administration (SSH, Jenkins, API Kubernetes)"
  type        = list(string)
}

variable "app_allowed_cidrs" {
  description = "CIDR autorisés vers l'application (NodePorts)"
  type        = list(string)
}

variable "alert_email" {
  description = "E-mail abonné aux alarmes (vide = aucun)"
  type        = string
  default     = ""
}

variable "instances" {
  description = "Instances à créer, par nom"
  type = map(object({
    role          = string
    instance_type = string
    volume_size   = number
  }))
}
