.PHONY: help install install-dev setup test test-cli test-db test-storage clean format lint type-check quality build

# Default target
help:
	@echo "dbVault Development Commands"
	@echo "==========================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install core dependencies"
	@echo "  make install-dev   Install development dependencies"
	@echo "  make setup         Complete development environment setup"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-cli      Run CLI tests only"
	@echo "  make test-db       Run database tests only"
	@echo "  make test-storage  Run storage tests only"
	@echo ""
	@echo "Code Quality:"
	@echo "  make format        Format code with black"
	@echo "  make lint          Lint code with flake8"
	@echo "  make type-check    Type check with mypy"
	@echo "  make quality       Run all quality checks"
	@echo ""
	@echo "Build:"
	@echo "  make build         Build wheel package"
	@echo "  make clean         Clean up containers and cache"

# Installation targets
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

setup:
	./scripts/setup-dev.sh

# Testing targets
test:
	./scripts/run-tests.sh

test-cli:
	pytest tests/test_cli.py -v

test-db:
	pytest tests/test_database.py -v

test-storage:
	pytest tests/test_storage.py -v

# Code quality targets
format:
	black src/ tests/

lint:
	flake8 src/ tests/

type-check:
	mypy src/

quality: format lint type-check
	@echo "✅ All quality checks passed!"

# Build targets
build:
	pip install build
	python -m build

# Cleanup targets
clean:
	./scripts/cleanup.sh
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	rm -rf dist/ build/ htmlcov/
