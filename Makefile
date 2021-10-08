.PHONY: install dist update
SHELL=/bin/bash
DATETIME:=$(shell date -u +%Y%m%dT%H%M%SZ)
ECR_REGISTRY=672626379771.dkr.ecr.us-east-1.amazonaws.com

help: ## Print this message
	@awk 'BEGIN { FS = ":.*##"; print "Usage:  make <target>\n\nTargets:" } \
/^[-_[:alpha:]]+:.?*##/ { printf "  %-15s%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install: ## Install dependencies, including dev dependencies
	pipenv install --dev

dist: ## Build docker container
	docker build -t $(ECR_REGISTRY)/dspacesubmissionservice-stage:latest \
		-t $(ECR_REGISTRY)/dspacesubmissionservice-stage:`git describe --always` \
		-t submitter:latest .	

update: install ## Update all Python dependencies
	pipenv clean
	pipenv update --dev

publish: dist ## Build, tag and push
	docker login -u AWS -p $$(aws ecr get-login-password --region us-east-1) $(ECR_REGISTRY)
	docker push $(ECR_REGISTRY)/dspacesubmissionservice-stage:latest
	docker push $(ECR_REGISTRY)/dspacesubmissionservice-stage:`git describe --always`

run-stage: 
	aws ecs run-task --cluster dspacesubmissionservice-stage --task-definition dspacesubmissionservice-stage --network-configuration "awsvpcConfiguration={subnets=[subnet-0744a5c9beeb49a20],securityGroups=[sg-06b90b77a06e5870a],assignPublicIp=DISABLED}" --launch-type FARGATE --region us-east-1

lint: bandit black flake8 isort ## Runs all linters

bandit: ## Security oriented static analyser for python code
	pipenv run bandit -r submitter

black: ## The Uncompromising Code Formatter
	pipenv run black --check --diff .

flake8: ## Tool For Style Guide Enforcement
	pipenv run flake8 .

isort: ## isort your imports, so you don't have to
	pipenv run isort . --diff

test: ## runs pytest
	pipenv run pytest --cov=submitter

coveralls: test
	pipenv run coveralls
