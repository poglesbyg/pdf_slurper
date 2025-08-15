#!/bin/bash
# Test runner script for PDF Slurper

set -e

echo "========================================="
echo "PDF Slurper Test Suite"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv is not installed${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
uv sync --all-extras

# Run linting
echo -e "\n${YELLOW}Running linting...${NC}"
uv run ruff check src/ tests/ || true

# Run type checking
echo -e "\n${YELLOW}Running type checking...${NC}"
uv run mypy src/ || true

# Run unit tests
echo -e "\n${YELLOW}Running unit tests...${NC}"
uv run pytest tests/unit/ -v --tb=short

# Run integration tests
echo -e "\n${YELLOW}Running integration tests...${NC}"
uv run pytest tests/integration/ -v --tb=short || true

# Run with coverage
echo -e "\n${YELLOW}Running tests with coverage...${NC}"
uv run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

echo -e "\n${GREEN}========================================="
echo "Test suite completed!"
echo "Coverage report: htmlcov/index.html"
echo -e "=========================================${NC}"
