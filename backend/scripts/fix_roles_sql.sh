#!/bin/bash
# SQL script to directly update user roles in production database
# Run this on the EC2 instance where the app is deployed

cat << 'SQL' | psql $DATABASE_URL
-- Bootstrap admin and other demo user roles

UPDATE users SET role = 'ADMIN' 
WHERE email = 'admin@demo.swadely.com';

UPDATE users SET role = 'COMPLIANCE_OFFICER' 
WHERE email = 'compliance@demo.swadely.com';

UPDATE users SET role = 'ISSUER' 
WHERE email IN ('issuer1@demo.swadely.com', 'issuer2@demo.swadely.com');

-- Investors already have INVESTOR role from registration

SELECT id, email, role, full_name 
FROM users 
WHERE email LIKE '%@demo.swadely.com' 
ORDER BY role, email;
SQL

echo ""
echo "✓ User roles updated successfully"
