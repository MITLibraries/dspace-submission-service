SHELL=/bin/bash
DATETIME:=$(shell date -u +%Y%m%dT%H%M%SZ)

help: # Preview Makefile commands
	@awk 'BEGIN { FS = ":.*#"; print "Usage:  make <target>\n\nTargets:" } \
/^[-_[:alpha:]]+:.?*#/ { printf "  %-15s%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

#######################
# Dependency commands
#######################

install: # Install Python dependencies
	pipenv install --dev
	pipenv run pre-commit install

update: install # Update Python dependencies
	pipenv clean
	pipenv update --dev


######################
# Unit test commands
######################

test: # Run tests and print a coverage report
	pipenv run coverage run --source=submitter -m pytest -vv
	pipenv run coverage report -m

coveralls: test # Write coverage data to an LCOV report
	pipenv run coverage lcov -o ./coverage/lcov.info


####################################
# Code quality and safety commands
####################################

lint: black mypy ruff safety # Run linters

black: # Run 'black' linter and print a preview of suggested changes
	pipenv run black --check --diff .

mypy: # Run 'mypy' linter
	pipenv run mypy .

ruff: # Run 'ruff' linter and print a preview of errors
	pipenv run ruff check .

safety: # Check for security vulnerabilities and verify Pipfile.lock is up-to-date
	pipenv run pip-audit
	pipenv verify

lint-apply: black-apply ruff-apply # Apply changes with 'black' and resolve 'fixable errors' with 'ruff'

black-apply: # Apply changes with 'black'
	pipenv run black .

ruff-apply: # Resolve 'fixable errors' with 'ruff'
	pipenv run ruff check --fix .

### This is the Terraform-generated header for dspace-submission-service-dev. If  ###
###   this is a Lambda repo, uncomment the FUNCTION line below  ###
###   and review the other commented lines in the document.     ###
ECR_NAME_DEV:=dspace-submission-service-dev
ECR_URL_DEV:=222053980223.dkr.ecr.us-east-1.amazonaws.com/dspace-submission-service-dev
# FUNCTION_DEV:=
### End of Terraform-generated header                            ###

### Terraform-generated Developer Deploy Commands for Dev environment ###
dist-dev: ## Build docker container (intended for developer-based manual build)
	docker build --platform linux/amd64 \
	    -t $(ECR_URL_DEV):latest \
		-t $(ECR_URL_DEV):`git describe --always` \
		-t $(ECR_NAME_DEV):latest .

publish-dev: dist-dev ## Build, tag and push (intended for developer-based manual publish)
	docker login -u AWS -p $$(aws ecr get-login-password --region us-east-1) $(ECR_URL_DEV)
	docker push $(ECR_URL_DEV):latest
	docker push $(ECR_URL_DEV):`git describe --always`

### If this is a Lambda repo, uncomment the two lines below     ###
# update-lambda-dev: ## Updates the lambda with whatever is the most recent image in the ecr (intended for developer-based manual update)
#	aws lambda update-function-code --function-name $(FUNCTION_DEV) --image-uri $(ECR_URL_DEV):latest


### Terraform-generated manual shortcuts for deploying to Stage. This requires  ###
###   that ECR_NAME_STAGE, ECR_URL_STAGE, and FUNCTION_STAGE environment        ###
###   variables are set locally by the developer and that the developer has     ###
###   authenticated to the correct AWS Account. The values for the environment  ###
###   variables can be found in the stage_build.yml caller workflow.            ###
dist-stage: ## Only use in an emergency
	docker build --platform linux/amd64 \
	    -t $(ECR_URL_STAGE):latest \
		-t $(ECR_URL_STAGE):`git describe --always` \
		-t $(ECR_NAME_STAGE):latest .

publish-stage: ## Only use in an emergency
	docker login -u AWS -p $$(aws ecr get-login-password --region us-east-1) $(ECR_URL_STAGE)
	docker push $(ECR_URL_STAGE):latest
	docker push $(ECR_URL_STAGE):`git describe --always`

### If this is a Lambda repo, uncomment the two lines below     ###
# update-lambda-stage: ## Updates the lambda with whatever is the most recent image in the ecr (intended for developer-based manual update)
#	aws lambda update-function-code --function-name $(FUNCTION_STAGE) --image-uri $(ECR_URL_STAGE):latest

run-dev:  ## Runs the task in dev - see readme for more info
	aws ecs run-task --cluster DSS-SubmissionService-dev --task-definition DSS-SubmissionService-dev --network-configuration "awsvpcConfiguration={subnets=[subnet-0488e4996ddc8365b,subnet-022e9ea19f5f93e65],securityGroups=[sg-044033bf5f102c544],assignPublicIp=DISABLED}" --launch-type FARGATE --region us-east-1

verify-dspace-connection-dev: # Verify dev app can connect to DSpace
	aws ecs run-task --cluster DSS-SubmissionService-dev --task-definition DSS-SubmissionService-dev --network-configuration "awsvpcConfiguration={subnets=[subnet-0488e4996ddc8365b,subnet-022e9ea19f5f93e65],securityGroups=[sg-044033bf5f102c544],assignPublicIp=DISABLED}" --launch-type FARGATE --region us-east-1 --overrides '{"containerOverrides": [ {"name": "DSS", "command": ["verify-dspace-connection"]}]}'

run-stage:  ## Runs the task in stage - see readme for more info
	aws ecs run-task --cluster DSS-SubmissionService-stage --task-definition DSS-SubmissionService-stage --network-configuration "awsvpcConfiguration={subnets=[subnet-05df31ac28dd1a4b0,subnet-04cfa272d4f41dc8a],securityGroups=[sg-0f64d9a1101d544d1],assignPublicIp=DISABLED}" --launch-type FARGATE --region us-east-1

verify-dspace-connection-stage: # Verify stage app can connect to DSpace
	aws ecs run-task --cluster DSS-SubmissionService-stage --task-definition DSS-SubmissionService-stage --network-configuration "awsvpcConfiguration={subnets=[subnet-05df31ac28dd1a4b0,subnet-04cfa272d4f41dc8a],securityGroups=[sg-0f64d9a1101d544d1],assignPublicIp=DISABLED}" --launch-type FARGATE --region us-east-1 --overrides '{"containerOverrides": [ {"name": "DSS", "command": ["verify-dspace-connection"]}]}'

run-prod:  ## Runs the task in prod - see readme for more info
	aws ecs run-task --cluster DSS-SubmissionService-prod --task-definition DSS-SubmissionService-prod --network-configuration "awsvpcConfiguration={subnets=[subnet-042726f373a7c5a79,subnet-05ab0e5c2bfcd748f],securityGroups=[sg-0325d8c490a870a90],assignPublicIp=DISABLED}" --launch-type FARGATE --region us-east-1

verify-dspace-connection-prod: # Verify prod app can connect to DSpace
	aws ecs run-task --cluster DSS-SubmissionService-prod --task-definition DSS-SubmissionService-prod --network-configuration "awsvpcConfiguration={subnets=[subnet-042726f373a7c5a79,subnet-05ab0e5c2bfcd748f],securityGroups=[sg-0325d8c490a870a90],assignPublicIp=DISABLED}" --launch-type FARGATE --region us-east-1 --overrides '{"containerOverrides": [ {"name": "DSS", "command": ["verify-dspace-connection"]}]}'

# run-prod: ## Runs the task in stage - see readme for more info
#   Not yet deployed in production

# verify-dspace-connection-prod: # Verify prod app can connect to DSpace
# 	Not yet deployed in production