SHELL=/bin/bash
DATETIME:=$(shell date -u +%Y%m%dT%H%M%SZ)

### This is the Terraform-generated header for                          ###
### dspace-submission-service-dev. If this is a Lambda repo, uncomment  ###
### the FUNCTION line below and review the other commented lines in the ###
### document.                                                           ###
ECR_NAME_DEV := dspace-submission-service-dev
ECR_URL_DEV := 222053980223.dkr.ecr.us-east-1.amazonaws.com/dspace-submission-service-dev
CPU_ARCH ?= $(shell cat .aws-architecture 2>/dev/null || echo \"linux/amd64\")
# FUNCTION_DEV := 
### End of Terraform-generated header                            ###

.PHONY: help install venv update test coveralls lint lint-fix security check-arch dist-dev publish-dev docker-clean

help: # Preview Makefile commands
	@awk 'BEGIN { FS = ":.*#"; print "Usage:  make <target>\n\nTargets:" } \
/^[-_[:alpha:]]+:.?*#/ { printf "  %-15s%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

##############################################
# Python Environment and Dependency commands
##############################################

install: .venv .git/hooks/pre-commit .git/hooks/pre-push # Install Python dependencies and create virtual environment if not exists
	uv sync --dev

.venv: # Creates virtual environment if not found
	@echo "Creating virtual environment at .venv..."
	uv venv .venv

.git/hooks/pre-commit: # Sets up pre-commit commit hooks if not setup
	@echo "Installing pre-commit commit hooks..."
	uv run pre-commit install --hook-type pre-commit

.git/hooks/pre-push: # Sets up pre-commit push hooks if not setup
	@echo "Installing pre-commit push hooks..."
	uv run pre-commit install --hook-type pre-push

venv: .venv # Create the Python virtual environment

update: # Update Python dependencies
	uv lock --upgrade
	uv sync --dev

######################
# Unit test commands
######################

test: # Run tests and print a coverage report
	uv run coverage run --source=submitter -m pytest -vv
	uv run coverage report -m

coveralls: test # Write coverage data to an LCOV report
	uv run coverage lcov -o ./coverage/lcov.info

####################################
# Code linting and formatting
####################################

lint: # Run linting, alerts only, no code changes
	uv run ruff format --diff
	uv run ruff check .
	uv run mypy .

lint-fix: # Run linting, auto fix behaviors where supported
	uv run ruff format .
	uv run ruff check --fix .

security: # Run security / vulnerability checks
	uv run pip-audit

run-dev:  ## Runs the task in dev - see readme for more info
	aws ecs run-task \
		--cluster dso-ecs-dev \
		--task-definition dso-dss-dev \
		--propagate-tags "TASK_DEFINITION" \
		--network-configuration "awsvpcConfiguration={subnets=[subnet-0488e4996ddc8365b,subnet-022e9ea19f5f93e65],securityGroups=[sg-01fd0496045d1d8ef],assignPublicIp=DISABLED}" \
		--launch-type FARGATE \
		--region us-east-1

run-stage:  ## Runs the task in stage - see readme for more info
	aws ecs run-task \
		--cluster dso-ecs-stage \
		--task-definition dso-dss-stage \
		--propagate-tags "TASK_DEFINITION" \
		--network-configuration "awsvpcConfiguration={subnets=[subnet-05df31ac28dd1a4b0,subnet-04cfa272d4f41dc8a],securityGroups=[sg-0f64d9a1101d544d1],assignPublicIp=DISABLED}" \
		--launch-type FARGATE \
		--region us-east-1

run-prod:  ## Runs the task in prod - see readme for more info
	aws ecs run-task \
		--cluster dso-ecs-prod \
		--task-definition dso-dss-prod \
		--propagate-tags "TASK_DEFINITION" \
		--network-configuration "awsvpcConfiguration={subnets=[subnet-042726f373a7c5a79,subnet-05ab0e5c2bfcd748f],securityGroups=[sg-0325d8c490a870a90],assignPublicIp=DISABLED}" \
		--launch-type FARGATE \
		--region us-east-1

### Terraform-generated Developer Deploy Commands for Dev environment ###
check-arch:
	@ARCH_FILE=".aws-architecture"; \
	if [[ "$(CPU_ARCH)" != "linux/amd64" && "$(CPU_ARCH)" != "linux/arm64" ]]; then \
		echo "Invalid CPU_ARCH: $(CPU_ARCH)"; exit 1; \
	fi; \
	if [[ -f $$ARCH_FILE ]]; then \
		echo "latest-$(shell echo $(CPU_ARCH) | cut -d'/' -f2)" > .arch_tag; \
	else \
		echo "latest" > .arch_tag; \
	fi

dist-dev: check-arch ## Build docker container (intended for developer-based manual build)
	@ARCH_TAG=$$(cat .arch_tag); \
	docker buildx inspect $(ECR_NAME_DEV) >/dev/null 2>&1 || docker buildx create --name $(ECR_NAME_DEV) --use; \
	docker buildx use $(ECR_NAME_DEV); \
	docker buildx build --platform $(CPU_ARCH) \
			--load \
			--tag $(ECR_URL_DEV):$$ARCH_TAG \
			--tag $(ECR_URL_DEV):make-$$ARCH_TAG \
			--tag $(ECR_URL_DEV):make-$(shell git describe --always) \
			--tag $(ECR_NAME_DEV):$$ARCH_TAG \
			.

publish-dev: dist-dev ## Build, tag and push (intended for developer-based manual publish)
	@ARCH_TAG=$$(cat .arch_tag); \
	aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(ECR_URL_DEV); \
	docker push $(ECR_URL_DEV):$$ARCH_TAG; \
	docker push $(ECR_URL_DEV):make-$$ARCH_TAG; \
	docker push $(ECR_URL_DEV):make-$(shell git describe --always); \
	echo "Cleaning up dangling Docker images..."; \
	docker image prune -f --filter "dangling=true"

### If this is a Lambda repo, uncomment the two lines below     ###
# update-lambda-dev: ## Updates the lambda with whatever is the most recent image in the ecr (intended for developer-based manual update)
#	@ARCH_TAG=$$(cat .arch_tag); \
#	aws lambda update-function-code \
#		--region us-east-1 \
#		--function-name $(FUNCTION_DEV) \
#		--image-uri $(ECR_URL_DEV):make-$$ARCH_TAG

docker-clean: ## Clean up Docker detritus
	@ARCH_TAG=$$(cat .arch_tag); \
	echo "Cleaning up Docker leftovers (containers, images, builders)"; \
	docker rmi -f $(ECR_URL_DEV):$$ARCH_TAG; \
	docker rmi -f $(ECR_URL_DEV):make-$$ARCH_TAG; \
	docker rmi -f $(ECR_URL_DEV):make-$(shell git describe --always) || true; \
	docker rmi -f $(ECR_NAME_DEV):$$ARCH_TAG || true; \
	docker buildx rm $(ECR_NAME_DEV) || true
	@rm -rf .arch_tag
