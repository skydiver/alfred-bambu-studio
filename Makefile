.PHONY: help dist install test clean

# Alfred runs the script with the system interpreter, so tests use the same one.
PYTHON := /usr/bin/python3
DIST := dist
ARTIFACT := $(DIST)/Bambu-Recent.alfredworkflow
# Files packaged into the workflow. icon.png is optional until one is added.
SOURCES := info.plist bambu_recent.py $(wildcard icon.png)

# Running `make` with no target only lists what is available.
.DEFAULT_GOAL := help

help: ## Show this help
	@echo "Bambu Recent — available targets:\n"
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'
	@echo ""

# Always rebuilt from scratch, so a removed source never lingers in the archive.
dist: ## Package the workflow into dist/
	@mkdir -p $(DIST)
	@rm -f $(ARTIFACT)
	zip -X -q $(ARTIFACT) $(SOURCES)
	@echo "\n✅ Build complete. Output:"
	@ls -lh $(ARTIFACT)
	@echo "\nInstall:  make install"

install: dist ## Build and import the workflow into Alfred
	open $(ARTIFACT)

test: ## Run the unit tests
	$(PYTHON) -m unittest discover -s tests -t . -v

clean: ## Remove dist/ and Python caches
	rm -rf $(DIST)
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
