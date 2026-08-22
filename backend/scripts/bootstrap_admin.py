#!/usr/bin/env python3
"""
Bootstrap first ADMIN user by directly updating the database.

This script solves the chicken-and-egg problem: you need an ADMIN to promote
users to ADMIN via the API, but you can't create the first ADMIN through the API.

Usage:
    python3 scripts/bootstrap_admin.py <user_email>

Example:
    python3 scripts/bootstrap_admin.py admin@demo.swadely.com
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def bootstrap_admin(email: str):
    """Promote a user to ADMIN role by directly updating the database."""

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url)

    async with engine.begin() as conn:
        # Check if user exists
        result = await conn.execute(
            text("SELECT id, email, role, full_name FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.fetchone()

        if not user:
            print(f"ERROR: User with email '{email}' not found in database")
            print("\nAvailable users:")
            result = await conn.execute(text("SELECT id, email, role, full_name FROM users ORDER BY id"))
            for row in result.fetchall():
                print(f"  {row[0]}: {row[1]} ({row[2]}) - {row[3]}")
            sys.exit(1)

        user_id, current_email, current_role, full_name = user

        if current_role == "ADMIN":
            print(f"✓ User '{current_email}' is already an ADMIN")
            return

        # Update role to ADMIN
        await conn.execute(
            text("UPDATE users SET role = 'ADMIN' WHERE id = :id"),
            {"id": user_id}
        )

        print(f"✓ Successfully promoted user to ADMIN:")
        print(f"  ID: {user_id}")
        print(f"  Email: {current_email}")
        print(f"  Name: {full_name}")
        print(f"  Previous role: {current_role}")
        print(f"  New role: ADMIN")
        print(f"\nYou can now login with:")
        print(f"  Email: {current_email}")
        print(f"  Password: (your password)")

    await engine.dispose()


async def main():
    if len(sys.argv) != 2:
        print("Usage: python3 scripts/bootstrap_admin.py <user_email>")
        print("\nExample:")
        print("  python3 scripts/bootstrap_admin.py admin@demo.swadely.com")
        sys.exit(1)

    email = sys.argv[1]
    await bootstrap_admin(email)


if __name__ == "__main__":
    asyncio.run(main())
