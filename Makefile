.DEFAULT_GOAL := help
SHELL := /bin/bash

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

test: ## Tests unitaires de l'application
	cd app && python -m pytest -q

lint: ## yamllint + ansible-lint + terraform fmt + kubeconform
	cd Ansible && yamllint -c .yamllint . && ansible-lint playbooks roles
	terraform -chdir=terraform fmt -check -recursive
	kustomize build k8s-manifests | kubeconform -strict -summary

docker-build: ## Construit l'image en local
	docker build -t ivolve-webapp:local app

docker-run: docker-build ## Lance l'image sur http://localhost:5000
	docker run --rm -p 5000:5000 ivolve-webapp:local

tf-init: ## terraform init (copiez d'abord terraform/backend.hcl.example en backend.hcl)
	terraform -chdir=terraform init -backend-config=backend.hcl

tf-plan: ## terraform plan
	terraform -chdir=terraform plan

tf-apply: ## terraform apply
	terraform -chdir=terraform apply

ansible-deps: ## Installe les collections Ansible
	cd Ansible && ansible-galaxy collection install -r requirements.yml -p collections

ansible-all: ## Déploie Jenkins + Kubernetes + supervision
	cd Ansible && ansible-playbook playbooks/site.yml

architecture: ## Régénère docs/architecture.gif
	python3 scripts/make_architecture_gif.py

.PHONY: help test lint docker-build docker-run tf-init tf-plan tf-apply ansible-deps ansible-all architecture
