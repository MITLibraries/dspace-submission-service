.PHONY: install dist update
SHELL=/bin/bash
DATETIME:=$(shell date -u +%Y%m%dT%H%M%SZ)


help: ## Print this message
	@awk 'BEGIN { FS = ":.*##"; print "Usage:  make <target>\n\nTargets:" } \
/^[-_[:alpha:]]+:.?*##/ { printf "  %-15s%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install:
	pipenv install

dist: ## Build docker container
	docker build -t submitter .

update: install ## Update all Python dependencies
	pipenv clean
	pipenv update --dev
