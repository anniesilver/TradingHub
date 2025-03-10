.DEFAULT_GOAL=help

# Required for globs to work correctly
SHELL := /bin/bash
PYTHON := python3.9

.EXPORT_ALL_VARIABLES:

ROOT_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
VENV_DIR = $(ROOT_DIR)/.venv

.PHONY: all
all: venv format lint test  ## Build all common targets

.PHONY: format
format:  ## Format all python code
	@echo "==> Formatting all python code"
	@$(VENV_DIR)/bin/black . \
		--line-length=79 \
		--skip-string-normalization
	@$(VENV_DIR)/bin/isort . \
		--profile black

.PHONY: lint
lint:  ## Run static code analysis
	@echo "==> Running static code analysis"
	@echo "==> Running flake8 ..."
	@$(VENV_DIR)/bin/flake8 . \
		--exclude $(VENV_DIR)
	@echo "==> Running pylint ..."
	@$(VENV_DIR)/bin/pylint . \
		--ignore-paths $(VENV_DIR)
	@echo "==> Running mypy ..."
	@$(VENV_DIR)/bin/mypy . \
		--exclude $(VENV_DIR)

.PHONY: venv
venv:  ## kick off venv
	@echo "==> Setting up virtual environment"
	@$(PYTHON) -m venv --upgrade-deps $(VENV_DIR)
	@$(VENV_DIR)/bin/pip install -qr $(ROOT_DIR)/requirements.txt

.PHONY: tools
tools: venv ## install dev tools
	@echo "==> Installing build tools"
	@$(VENV_DIR)/bin/pip install -qr $(ROOT_DIR)/requirements-tools.txt

.PHONY: test
test:  ## Run unit tests
	@echo "==> Running unit tests"
	@$(VENV_DIR)/bin/pytest -v --cov --cov-report=term --cov-report=html:build/ .

.PHONY: clean
clean:  ## clean up temporary files
	@echo "==> Removing temporary files from build and test"
	@# purposely deal with .venv under current dir to avoid excessive redo venv
	@for TEMP in .venv .coverage .mypy_cache .pytest_cache __pycache__ build; do \
		find . -name $${TEMP} | xargs rm -rf ; \
	done

.PHONY: help
help:  ## Print list of Makefile targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  cut -d ":" -f1- | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
