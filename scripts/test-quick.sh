#!/bin/bash
# Quick test script for Austial/Swadely platform
# Run from austial-hackathon/ root directory

set -e

echo "🧪 Austial/Swadely Quick Test Suite"
echo "===================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Backend tests
echo -e "${BLUE}📦 Backend Unit Tests${NC}"
cd backend/
uv run pytest tests/unit/ -v --tb=short || {
  echo -e "${RED}❌ Backend unit tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ Backend unit tests passed${NC}"
echo ""

# Backend integration tests
echo -e "${BLUE}🔗 Backend Integration Tests${NC}"
uv run pytest tests/integration/ -v --tb=short || {
  echo -e "${RED}❌ Backend integration tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ Backend integration tests passed${NC}"
echo ""

# Frontend tests
echo -e "${BLUE}🎨 Frontend Tests${NC}"
cd ../frontend/
npm test -- --watch=false --browsers=ChromeHeadless || {
  echo -e "${RED}❌ Frontend tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ Frontend tests passed${NC}"
echo ""

# Type checking
echo -e "${BLUE}🔍 Backend Type Checking${NC}"
cd ../backend/
uv run mypy src/ --ignore-missing-imports || {
  echo -e "${RED}❌ Backend type checking failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ Backend type checking passed${NC}"
echo ""

# Linting
echo -e "${BLUE}✨ Backend Linting${NC}"
uv run ruff check src/ || {
  echo -e "${RED}❌ Backend linting failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ Backend linting passed${NC}"
echo ""

echo -e "${GREEN}🎉 All tests passed!${NC}"
