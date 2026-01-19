.PHONY: help build universal clean workflow install lint test

BINARY_NAME=lbsearch
WORKFLOW_NAME=letterboxd.alfredworkflow
VERSION?=$(shell (git describe --tags --always --dirty 2>/dev/null || echo "dev") | sed 's/^v//')
LDFLAGS=-ldflags="-s -w -X main.version=$(VERSION)"

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

build: ## Build the binary for current architecture
	@echo "Building $(BINARY_NAME) version $(VERSION)..."
	go build -o $(BINARY_NAME) $(LDFLAGS) .
	@echo "Done! Binary: $(BINARY_NAME)"

universal: ## Build universal binary (Intel + Apple Silicon)
	@echo "Building universal binary version $(VERSION)..."
	@GOOS=darwin GOARCH=amd64 go build -o $(BINARY_NAME)-amd64 $(LDFLAGS) .
	@GOOS=darwin GOARCH=arm64 go build -o $(BINARY_NAME)-arm64 $(LDFLAGS) .
	@lipo -create $(BINARY_NAME)-amd64 $(BINARY_NAME)-arm64 -output $(BINARY_NAME)
	@rm $(BINARY_NAME)-amd64 $(BINARY_NAME)-arm64
	@echo "Done! Universal binary: $(BINARY_NAME)"
	@file $(BINARY_NAME)

clean: ## Remove built files
	@echo "Cleaning..."
	rm -f $(BINARY_NAME) $(BINARY_NAME)-amd64 $(BINARY_NAME)-arm64
	rm -f $(WORKFLOW_NAME)
	@echo "Done!"

workflow: clean universal ## Build the Alfred workflow package with universal binary
	@echo "Creating $(WORKFLOW_NAME) version $(VERSION)..."
	@plutil -replace version -string "$(VERSION)" info.plist
	@zip $(WORKFLOW_NAME) info.plist icon.png $(BINARY_NAME) > /dev/null
	@plutil -replace version -string "dev" info.plist
	@echo "Done! Workflow: $(WORKFLOW_NAME)"
	@ls -lh $(WORKFLOW_NAME)

install: workflow ## Build and install the workflow in Alfred
	@echo "Installing workflow..."
	@open $(WORKFLOW_NAME)
	@echo "Done! The workflow should now be installed in Alfred."

lint: ## Run golangci-lint
	@echo "Running golangci-lint..."
	@golangci-lint run
	@echo "✓ Linting passed!"

test: build ## Run tests
	@echo "Running Go tests..."
	@go test ./...
	@echo "Testing film search..."
	@./$(BINARY_NAME) films "raiders of the lost ark" | jq -e '.items[0].title' > /dev/null && echo "✓ Film search works"
	@echo "Testing people search..."
	@./$(BINARY_NAME) people "harrison ford" | jq -e '.items[0].title' > /dev/null && echo "✓ People search works"
	@echo "All tests passed!"

.DEFAULT_GOAL := help
