#!/bin/bash
# Fix demo user roles by connecting to RDS from local machine
# This requires the RDS instance to be publicly accessible or VPN/bastion access

set -e

echo "🔧 Fixing demo user roles in production database..."
echo ""

# RDS connection details (update these based on your terraform outputs)
RDS_HOST="austial-demo-db.cqmxvvxvxvxv.us-east-1.rds.amazonaws.com"  # Update with actual endpoint
RDS_PORT="5432"
RDS_DB="austial"
RDS_USER="austial_admin"
RDS_PASSWORD="${RDS_PASSWORD:-}"  # Set this environment variable

if [ -z "$RDS_PASSWORD" ]; then
  echo "❌ ERROR: RDS_PASSWORD environment variable not set"
  echo ""
  echo "Usage:"
  echo "  export RDS_PASSWORD='your-rds-password'"
  echo "  bash scripts/fix_demo_roles_remote.sh"
  exit 1
fi

# Check if psql is installed
if ! command -v psql &> /dev/null; then
  echo "❌ ERROR: psql command not found"
  echo "Install it with: sudo apt-get install postgresql-client"
  exit 1
fi

echo "Connecting to RDS database..."
echo "Host: $RDS_HOST"
echo "Database: $RDS_DB"
echo ""

# Run the SQL updates
PGPASSWORD="$RDS_PASSWORD" psql -h "$RDS_HOST" -p "$RDS_PORT" -U "$RDS_USER" -d "$RDS_DB" << 'SQL'
-- Update demo user roles
UPDATE users SET role = 'ADMIN' WHERE email = 'admin@demo.swadely.com';
UPDATE users SET role = 'COMPLIANCE_OFFICER' WHERE email = 'compliance@demo.swadely.com';
UPDATE users SET role = 'ISSUER' WHERE email IN ('issuer1@demo.swadely.com', 'issuer2@demo.swadely.com');

-- Show updated users
SELECT id, email, role, full_name
FROM users
WHERE email LIKE '%@demo.swadely.com'
ORDER BY role, email;
SQL

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Demo user roles updated successfully!"
  echo ""
  echo "Updated roles:"
  echo "  • admin@demo.swadely.com → ADMIN"
  echo "  • compliance@demo.swadely.com → COMPLIANCE_OFFICER"
  echo "  • issuer1@demo.swadely.com → ISSUER"
  echo "  • issuer2@demo.swadely.com → ISSUER"
  echo "  • investor1/2/3@demo.swadely.com → INVESTOR (unchanged)"
  echo ""
  echo "🔐 All users still use password: Demo123!"
else
  echo ""
  echo "❌ Failed to update roles. Check your connection details and credentials."
  exit 1
fi
