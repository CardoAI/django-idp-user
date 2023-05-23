SHELL := /bin/sh
APP_NAME := idp_user
PROJECTNAME := $(shell basename $(CURDIR))


define HELP

Manage $(PROJECTNAME). Usage:

make lint           	Run linter
make format         	Run formatter
make test           	Run tests
make update-version 	Update version in readme.md
make pre-commit     	Install pre-commit hooks

endef

export HELP

lint:
	 @bash ./scripts/lint.sh

format:
	@bash ./scripts/format.sh

test:
	@bash ./scripts/test.sh

update-version:
	python ./scripts/update_version.py

pre-commit:
	pre-commit install

all help:
	@echo "$$HELP"
