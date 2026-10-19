# Backend distant S3 + verrou DynamoDB.
# Les noms (bucket, table) sont fournis à l'init pour éviter de les coder en dur :
#
#   terraform init -backend-config=backend.hcl        (voir backend.hcl.example)
#
# Les ressources S3/DynamoDB sont créées une seule fois par ./bootstrap.
terraform {
  backend "s3" {
    key     = "cloud-devops/terraform.tfstate"
    encrypt = true
  }
}
