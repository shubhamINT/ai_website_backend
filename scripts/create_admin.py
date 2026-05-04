"""
One-time script to seed the first admin user.

Usage:
    python -m scripts.create_admin --email admin@example.com --password secret
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.models.db_schemas import User
from src.core.database import close_db, get_database, init_db


async def create_admin(email: str, password: str) -> None:
    await init_db()
    db = get_database()

    existing = await db["users"].find_one({"email": email})
    if existing:
        print(f"ERROR: {email} already exists (role={existing['role']})")
        return

    await db["users"].insert_one(
        User(email=email, hashed_password=password, role="admin").model_dump()
    )
    print(f"Admin created: {email}")
    await close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed first admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    asyncio.run(create_admin(args.email, args.password))
