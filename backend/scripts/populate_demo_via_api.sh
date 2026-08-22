#!/bin/bash
# Populate demo data using the production API endpoints
# Run this script to create demo users and data for all roles

API_URL="http://52.6.51.39:8000"
PASSWORD="Demo123!"

echo "🚀 Creating demo data for Swadely/Austial platform..."
echo "API: $API_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to create user and get token
create_user() {
  local email=$1
  local role=$2
  local name=$3

  echo -e "${BLUE}Creating $role: $email${NC}"

  # Register user
  RESPONSE=$(curl -s -X POST "$API_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$email\",
      \"password\": \"$PASSWORD\",
      \"full_name\": \"$name\"
    }")

  USER_ID=$(echo $RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

  if [ -z "$USER_ID" ]; then
    echo -e "${RED}Failed to create user. Response: $RESPONSE${NC}"
    return 1
  fi

  echo -e "${GREEN}✓ User created (ID: $USER_ID)${NC}"

  # Login to get token
  TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$email\",
      \"password\": \"$PASSWORD\"
    }")

  TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

  if [ -z "$TOKEN" ]; then
    echo -e "${RED}Failed to get token${NC}"
    return 1
  fi

  echo -e "${GREEN}✓ Token obtained${NC}"
  echo "$USER_ID|$TOKEN"
}

# 1. Create ADMIN user first
echo "========================================="
echo "STEP 1: Creating ADMIN user"
echo "========================================="
ADMIN_INFO=$(create_user "admin@demo.swadely.com" "ADMIN" "Admin User")
ADMIN_ID=$(echo $ADMIN_INFO | cut -d'|' -f1)
ADMIN_TOKEN=$(echo $ADMIN_INFO | cut -d'|' -f2)
echo ""

# 2. Promote first user to ADMIN (self-promote for bootstrapping)
if [ ! -z "$ADMIN_TOKEN" ]; then
  echo "Promoting user to ADMIN role..."
  curl -s -X PATCH "$API_URL/admin/users/$ADMIN_ID/role" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"role": "ADMIN"}' > /dev/null
  echo -e "${GREEN}✓ Admin role assigned${NC}"
  echo ""
fi

# 3. Create COMPLIANCE_OFFICER
echo "========================================="
echo "STEP 2: Creating COMPLIANCE_OFFICER"
echo "========================================="
COMPLIANCE_INFO=$(create_user "compliance@demo.swadely.com" "COMPLIANCE_OFFICER" "Sarah Compliance")
COMPLIANCE_ID=$(echo $COMPLIANCE_INFO | cut -d'|' -f1)
COMPLIANCE_TOKEN=$(echo $COMPLIANCE_INFO | cut -d'|' -f2)

if [ ! -z "$ADMIN_TOKEN" ] && [ ! -z "$COMPLIANCE_ID" ]; then
  curl -s -X PATCH "$API_URL/admin/users/$COMPLIANCE_ID/role" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"role": "COMPLIANCE_OFFICER"}' > /dev/null
  echo -e "${GREEN}✓ Compliance Officer role assigned${NC}"
fi
echo ""

# 4. Create ISSUER users
echo "========================================="
echo "STEP 3: Creating ISSUER users"
echo "========================================="

ISSUER1_INFO=$(create_user "issuer1@demo.swadely.com" "ISSUER" "Acme Real Estate SPV")
ISSUER1_ID=$(echo $ISSUER1_INFO | cut -d'|' -f1)
ISSUER1_TOKEN=$(echo $ISSUER1_INFO | cut -d'|' -f2)

if [ ! -z "$ADMIN_TOKEN" ] && [ ! -z "$ISSUER1_ID" ]; then
  curl -s -X PATCH "$API_URL/admin/users/$ISSUER1_ID/role" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"role": "ISSUER"}' > /dev/null
  echo -e "${GREEN}✓ Issuer 1 role assigned${NC}"
fi

ISSUER2_INFO=$(create_user "issuer2@demo.swadely.com" "ISSUER" "GreenTech Bonds Ltd")
ISSUER2_ID=$(echo $ISSUER2_INFO | cut -d'|' -f1)
ISSUER2_TOKEN=$(echo $ISSUER2_INFO | cut -d'|' -f2)

if [ ! -z "$ADMIN_TOKEN" ] && [ ! -z "$ISSUER2_ID" ]; then
  curl -s -X PATCH "$API_URL/admin/users/$ISSUER2_ID/role" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"role": "ISSUER"}' > /dev/null
  echo -e "${GREEN}✓ Issuer 2 role assigned${NC}"
fi
echo ""

# 5. Create INVESTOR users
echo "========================================="
echo "STEP 4: Creating INVESTOR users"
echo "========================================="

INVESTOR1_INFO=$(create_user "investor1@demo.swadely.com" "INVESTOR" "Alice Johnson")
INVESTOR1_ID=$(echo $INVESTOR1_INFO | cut -d'|' -f1)
INVESTOR1_TOKEN=$(echo $INVESTOR1_INFO | cut -d'|' -f2)
echo ""

INVESTOR2_INFO=$(create_user "investor2@demo.swadely.com" "INVESTOR" "Bob Chen")
INVESTOR2_ID=$(echo $INVESTOR2_INFO | cut -d'|' -f1)
INVESTOR2_TOKEN=$(echo $INVESTOR2_INFO | cut -d'|' -f2)
echo ""

INVESTOR3_INFO=$(create_user "investor3@demo.swadely.com" "INVESTOR" "Carol Martinez")
INVESTOR3_ID=$(echo $INVESTOR3_INFO | cut -d'|' -f1)
INVESTOR3_TOKEN=$(echo $INVESTOR3_INFO | cut -d'|' -f2)
echo ""

# 6. Create Issuer Profiles
echo "========================================="
echo "STEP 5: Creating Issuer Profiles"
echo "========================================="

if [ ! -z "$ISSUER1_TOKEN" ]; then
  echo "Creating Issuer 1 profile..."
  curl -s -X POST "$API_URL/issuers/profile" \
    -H "Authorization: Bearer $ISSUER1_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "legal_name": "Acme Real Estate SPV Limited",
      "registration_number": "IFSC-SPV-2024-001",
      "registration_jurisdiction": "GIFT_CITY_IFSC"
    }' > /dev/null
  echo -e "${GREEN}✓ Issuer 1 profile created${NC}"
fi

if [ ! -z "$ISSUER2_TOKEN" ]; then
  echo "Creating Issuer 2 profile..."
  curl -s -X POST "$API_URL/issuers/profile" \
    -H "Authorization: Bearer $ISSUER2_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "legal_name": "GreenTech Infrastructure Bonds Ltd",
      "registration_number": "IFSC-BOND-2024-042",
      "registration_jurisdiction": "GIFT_CITY_IFSC"
    }' > /dev/null
  echo -e "${GREEN}✓ Issuer 2 profile created${NC}"
fi
echo ""

# 7. Create Investor Profiles (start KYC)
echo "========================================="
echo "STEP 6: Creating Investor Profiles"
echo "========================================="

if [ ! -z "$INVESTOR1_TOKEN" ]; then
  echo "Creating Investor 1 profile..."
  curl -s -X POST "$API_URL/investors/profile" \
    -H "Authorization: Bearer $INVESTOR1_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "date_of_birth": "1985-05-15",
      "nationality": "US",
      "tax_residence": "US",
      "phone": "+1-555-0101",
      "address_line1": "123 Wall Street",
      "address_city": "New York",
      "address_country": "US",
      "address_postal_code": "10005"
    }' > /dev/null
  echo -e "${GREEN}✓ Investor 1 profile created${NC}"
fi

if [ ! -z "$INVESTOR2_TOKEN" ]; then
  echo "Creating Investor 2 profile..."
  curl -s -X POST "$API_URL/investors/profile" \
    -H "Authorization: Bearer $INVESTOR2_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "date_of_birth": "1990-08-22",
      "nationality": "SG",
      "tax_residence": "SG",
      "phone": "+65-9876-5432",
      "address_line1": "1 Marina Boulevard",
      "address_city": "Singapore",
      "address_country": "SG",
      "address_postal_code": "018989"
    }' > /dev/null
  echo -e "${GREEN}✓ Investor 2 profile created${NC}"
fi

if [ ! -z "$INVESTOR3_TOKEN" ]; then
  echo "Creating Investor 3 profile..."
  curl -s -X POST "$API_URL/investors/profile" \
    -H "Authorization: Bearer $INVESTOR3_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
      "date_of_birth": "1988-12-03",
      "nationality": "MX",
      "tax_residence": "MX",
      "phone": "+52-55-1234-5678",
      "address_line1": "Av. Paseo de la Reforma 505",
      "address_city": "Mexico City",
      "address_country": "MX",
      "address_postal_code": "06500"
    }' > /dev/null
  echo -e "${GREEN}✓ Investor 3 profile created${NC}"
fi
echo ""

# Summary
echo "========================================="
echo "✅ DEMO DATA CREATION COMPLETE"
echo "========================================="
echo ""
echo "📋 Demo Credentials (Password: $PASSWORD for all)"
echo ""
echo "ADMIN:"
echo "  • admin@demo.swadely.com"
echo ""
echo "COMPLIANCE_OFFICER:"
echo "  • compliance@demo.swadely.com"
echo ""
echo "ISSUER:"
echo "  • issuer1@demo.swadely.com (Acme Real Estate SPV)"
echo "  • issuer2@demo.swadely.com (GreenTech Bonds)"
echo ""
echo "INVESTOR:"
echo "  • investor1@demo.swadely.com (Alice Johnson)"
echo "  • investor2@demo.swadely.com (Bob Chen)"
echo "  • investor3@demo.swadely.com (Carol Martinez)"
echo ""
echo "🌐 Frontend: http://austial-demo-frontend-459141725579.s3-website-us-east-1.amazonaws.com"
echo "🔌 Backend API: $API_URL"
echo ""
echo "💡 Next Steps:"
echo "  1. Login to frontend with any demo account"
echo "  2. Use COMPLIANCE_OFFICER to approve KYC for investors"
echo "  3. Use ADMIN to approve issuer profiles"
echo "  4. Use ISSUER to create assets and tokenization proposals"
echo "  5. Use INVESTOR to subscribe to tokens"
echo ""
