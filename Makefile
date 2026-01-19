.PHONY: help clean workflow install test lint

SCRIPT_NAME=lbsearch.py
WORKFLOW_NAME=letterboxd.alfredworkflow
VERSION?=$(shell (git describe --tags --always --dirty 2>/dev/null || echo "0.0.0") | sed 's/^v//')

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

clean: ## Remove built files
	@echo "Cleaning..."
	@rm -f $(WORKFLOW_NAME)
	@echo "Done!"

lint: ## Lint code with ruff
	@echo "Linting code..."
	@ruff format --check $(SCRIPT_NAME) tests/
	@ruff check $(SCRIPT_NAME) tests/
	@echo "✓ Linting passed"

test: ## Run unit and integration tests
	@echo "Running pytest..."
	@pytest tests/
	@echo "Testing film search (integration)..."
	@python3 $(SCRIPT_NAME) films "raiders of the lost ark" | jq -e '.items[0].title' > /dev/null && echo "✓ Film search works"
	@echo "Testing people search (integration)..."
	@python3 $(SCRIPT_NAME) people "harrison ford" | jq -e '.items[0].title' > /dev/null && echo "✓ People search works"
	@echo "All tests passed!"

workflow: clean ## Build the Alfred workflow package
	@echo "Creating $(WORKFLOW_NAME) version $(VERSION)..."
	@plutil -replace version -string "$(VERSION)" info.plist
	@sed -i '' 's/__version__ = ".*"/__version__ = "$(VERSION)"/' $(SCRIPT_NAME)
	@zip $(WORKFLOW_NAME) info.plist icon.png $(SCRIPT_NAME) > /dev/null
	@plutil -replace version -string "0.0.0" info.plist
	@sed -i '' 's/__version__ = ".*"/__version__ = "0.0.0"/' $(SCRIPT_NAME)
	@echo "Done! Workflow: $(WORKFLOW_NAME)"
	@ls -lh $(WORKFLOW_NAME)

install: workflow ## Build and install the workflow in Alfred
	@echo "Installing workflow..."
	@open $(WORKFLOW_NAME)
	@echo "Done! The workflow should now be installed in Alfred."

.DEFAULT_GOAL := help
