provider "aws" {
  region = var.aws_region

  # Tags appliqués automatiquement à toutes les ressources taguables
  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform"
    }
  }
}
