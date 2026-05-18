.PHONY: install test lint format clean build publish

install:
	pip install -e ".[full,dev]"

install-minimal:
	pip install -e .

test:
	pytest tests/ -v

lint:
	ruff check exort/

format:
	ruff format exort/

clean:
	rm -rf dist/ build/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build: clean
	python -m build

publish: build
	twine upload dist/*
