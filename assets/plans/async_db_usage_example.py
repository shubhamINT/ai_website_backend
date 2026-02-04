from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.api.models.db_schemas import MemoryEntry
from src.core.database import AsyncSessionLocal
import asyncio

async def example_usage():
    # 1. Getting a session manually (e.g., in a script or background task)
    async with AsyncSessionLocal() as db:
        # Create
        new_entry = MemoryEntry(
            content="Hello from the pool!",
            embedding=[0.1] * 1536
        )
        db.add(new_entry)
        await db.commit()
        await db.refresh(new_entry)
        print(f"Created entry with ID: {new_entry.id}")

        # Search / Select
        result = await db.execute(select(MemoryEntry).limit(10))
        entries = result.scalars().all()
        for entry in entries:
            print(f"Found: {entry.content}")

# 2. In FastAPI Routes
"""
from fastapi import Depends
from src.core.database import get_db

@router.get("/entries")
async def read_entries(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MemoryEntry))
    return result.scalars().all()
"""

if __name__ == "__main__":
    asyncio.run(example_usage())
