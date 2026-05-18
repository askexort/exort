.PHONY: install install-dev test lint format clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install the package
	pip install -e .

install-dev: ## Install with development dependencies
	pip install -e ".[dev,all]"

install-all: ## Install with all providers
	pip install -e ".[all]"

test: ## Run tests
	pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	pytest tests/ -v --cov=openmind --cov-report=term-missing

lint: ## Run linter
	ruff check openmind/ tests/

format: ## Format code
	ruff format openmind/ tests/

typecheck: ## Run type checker
	mypy openmind/

clean: ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

build: clean ## Build distribution
	python -m build

publish: build ## Publish to PyPI
	twine upload dist/*

demo: ## Run a quick demo
	openmind test --provider groq --query "What is the capital of France?"
