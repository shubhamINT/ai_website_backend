from sqlalchemy import Column, String, Integer, DateTime, func
from pgvector.sqlalchemy import Vector
from src.core.database import Base

class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    # 1536 is standard for OpenAI embeddings
    embedding = Column(Vector(1536)) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())
