.PHONY: install dist update
SHELL=/bin/bash
DATETIME:=$(shell date -u +%Y%m%dT%H%M%SZ)
ECR_REGISTRY=672626379771.dkr.ecr.us-east-1.amazonaws.com

help: ## Print this message
	@awk 'BEGIN { FS = ":.*##"; print "Usage:  make <target>\n\nTargets:" } \
/^[-_[:alpha:]]+:.?*##/ { printf "  %-15s%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install:
	pipenv install --dev

dist: ## Build docker container
	docker build -t $(ECR_REGISTRY)/dspacediscoveryservice-stage:latest \
		-t $(ECR_REGISTRY)/dspacediscoveryservice-stage:`git describe --always` \
		-t submitter:latest .	

update: install ## Update all Python dependencies
	pipenv clean
	pipenv update --dev

publish: dist ## Build, tag and push
	docker login -u AWS -p $$(aws ecr get-login-password --region us-east-1) $(ECR_REGISTRY)
	docker push $(ECR_REGISTRY)/dspacediscoveryservice-stage:latest
	docker push $(ECR_REGISTRY)/dspacediscoveryservice-stage:`git describe --always`