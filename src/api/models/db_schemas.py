from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from src.core.database import Base

# Example model:
# class UserMemory(Base):
#     __tablename__ = "user_memories"
#
#     id = Column(Integer, primary_key=True, index=True)
#     user_id = Column(String, index=True)
#     memory_type = Column(String)  # 'fact', 'preference', etc.
#     content = Column(JSON)
#     created_at = Column(DateTime(timezone=True), server_default=func.now())
#     updated_at = Column(DateTime(timezone=True), onupdate=func.now())
