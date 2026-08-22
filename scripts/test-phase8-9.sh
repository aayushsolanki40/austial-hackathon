#!/bin/bash
# Phase 8 (Compliance) & Phase 9 (ML) Testing Script
# Tests newly completed features: AML alerts, compliance reports, ML services

set -e

echo "🧪 Phase 8 & 9 Testing Suite"
echo "============================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cd backend/

echo -e "${BLUE}Phase 8: Compliance & Reporting${NC}"
echo "================================"
echo ""

# Test compliance module
echo -e "${YELLOW}Testing AML Alert service...${NC}"
uv run pytest tests/unit/compliance_service_spec.py -v -k "aml" || {
  echo -e "${RED}❌ AML service tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ AML service tests passed${NC}"
echo ""

echo -e "${YELLOW}Testing Compliance Report generation...${NC}"
uv run pytest tests/unit/compliance_service_spec.py -v -k "report" || {
  echo -e "${RED}❌ Compliance report tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ Compliance report tests passed${NC}"
echo ""

echo -e "${YELLOW}Testing Audit Log immutability...${NC}"
uv run pytest tests/unit/compliance_service_spec.py -v -k "audit" || {
  echo -e "${RED}❌ Audit log tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ Audit log tests passed${NC}"
echo ""

echo -e "${BLUE}Phase 9: AI/ML Layer${NC}"
echo "==================="
echo ""

# Test ML module
echo -e "${YELLOW}Testing KYC ML service (OCR, liveness, face matching)...${NC}"
uv run pytest tests/unit/ml_services_spec.py -v -k "kyc" || {
  echo -e "${RED}❌ KYC ML service tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ KYC ML service tests passed${NC}"
echo ""

echo -e "${YELLOW}Testing AML scoring service (XGBoost)...${NC}"
uv run pytest tests/unit/ml_services_spec.py -v -k "aml_scoring" || {
  echo -e "${RED}❌ AML scoring tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ AML scoring tests passed${NC}"
echo ""

echo -e "${YELLOW}Testing Valuation anomaly detection...${NC}"
uv run pytest tests/unit/ml_services_spec.py -v -k "anomaly" || {
  echo -e "${RED}❌ Valuation anomaly tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ Valuation anomaly tests passed${NC}"
echo ""

echo -e "${YELLOW}Testing ML prediction audit trail...${NC}"
uv run pytest tests/unit/ml_prediction_spec.py -v || {
  echo -e "${RED}❌ ML prediction audit tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ ML prediction audit tests passed${NC}"
echo ""

# Integration tests
echo -e "${BLUE}Integration Tests${NC}"
echo "=================="
echo ""

echo -e "${YELLOW}Testing Compliance → ML integration...${NC}"
uv run pytest tests/integration/test_compliance_aml_ml_integration.py -v || {
  echo -e "${RED}❌ Compliance-ML integration tests failed${NC}"
  exit 1
}
echo -e "${GREEN}✅ Compliance-ML integration tests passed${NC}"
echo ""

# API endpoint tests
echo -e "${BLUE}API Endpoint Tests${NC}"
echo "==================="
echo ""

# Test against production or local
API_URL="${API_URL:-http://52.6.51.39:8000}"
echo -e "${YELLOW}Testing against: $API_URL${NC}"
echo -e "${BLUE}(Set API_URL env var to test against different endpoint)${NC}"
echo ""

# Health check
echo -e "${YELLOW}Checking API health...${NC}"
if curl -f $API_URL/health > /dev/null 2>&1; then
  echo -e "${GREEN}✅ API is reachable${NC}"
else
  echo -e "${RED}❌ API health check failed${NC}"
  exit 1
fi

# Test Phase 8 endpoints
echo -e "${YELLOW}Testing /compliance/aml-alerts endpoint...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/compliance/aml-alerts)
if [ "$HTTP_CODE" == "401" ]; then
  echo -e "${GREEN}✅ Endpoint registered (auth required as expected)${NC}"
else
  echo -e "${RED}❌ Unexpected response: $HTTP_CODE${NC}"
  exit 1
fi

echo -e "${YELLOW}Testing /ml/models endpoint...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $API_URL/ml/models)
if [ "$HTTP_CODE" == "401" ]; then
  echo -e "${GREEN}✅ Endpoint registered (auth required as expected)${NC}"
else
  echo -e "${RED}❌ Unexpected response: $HTTP_CODE${NC}"
  exit 1
fi
echo ""

echo -e "${GREEN}🎉 Phase 8 & 9 tests passed!${NC}"
echo ""
echo "Next steps:"
echo "1. Run integration tests: uv run pytest tests/integration/"
echo "2. Test frontend compliance screens: cd ../frontend && npm start"
echo "3. Train XGBoost model: uv run python src/modules/ml/scripts/train_aml_model.py"
echo "4. See ../TESTING.md for detailed manual API testing instructions"
