from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, CheckConstraint, Float, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from datetime import datetime
import uuid

from src.core.database import Base


# Core user Identity
class User(Base):
    __tablename__ = "users"
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255))
    email = Column(String(255), unique=True)
    meta_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_active = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    memories = relationship("UserMemory", back_populates="user", cascade="all, delete-orphan")
    facts = relationship("UserFact", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_users_last_active', 'last_active', postgresql_using='btree', postgresql_ops={'last_active': 'DESC'}),
        Index('idx_users_meta_data', 'meta_data', postgresql_using='gin'),
    )

# Zep Layer - Track conversation sessions with temporal boundaries
class Session(Base):
    __tablename__ = "sessions"
    
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    session_type = Column(String(50), default="conversation")
    meta_data = Column(JSONB, default={})
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    ended_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("SessionMessage", back_populates="session", cascade="all, delete-orphan")
    ui_cards = relationship("UICardShown", back_populates="session", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_sessions_user_active', 'user_id', 'is_active'),
        Index('idx_sessions_started_at', 'started_at', postgresql_using='btree', postgresql_ops={'started_at': 'DESC'}),
        Index('idx_sessions_user_started', 'user_id', 'started_at', postgresql_using='btree', postgresql_ops={'started_at': 'DESC'}),
    )

# Zep Layer - Complete conversation replay with turn-based ordering
class SessionMessage(Base):
    __tablename__ = "session_messages"
    
    message_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    role = Column(String(20), CheckConstraint("role IN ('user', 'assistant', 'system')"), nullable=False)
    content = Column(Text, nullable=False)
    meta_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="messages")
    
    # Composite index for ordered retrieval
    __table_args__ = (
        Index('idx_messages_session_turn', 'session_id', 'turn_number'),
        Index('idx_messages_session_created', 'session_id', 'created_at'),
        Index('idx_messages_role', 'role'),
    )

# Zep Layer - Track UI cards shown at each conversation turn for voice navigation
class UICardShown(Base):
    __tablename__ = "ui_cards_shown"
    
    card_id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False)
    turn_number = Column(Integer, nullable=False)
    card_type = Column(String(100), nullable=False)
    card_data = Column(JSONB, nullable=False)
    display_order = Column(Integer, nullable=False)
    shown_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    
    # Relationships
    session = relationship("Session", back_populates="ui_cards")
    
    # Indexes for voice navigation queries
    __table_args__ = (
        Index('idx_cards_session_turn', 'session_id', 'turn_number'),
        Index('idx_cards_type', 'card_type'),
        Index('idx_cards_data', 'card_data', postgresql_using='gin'),
    )

# Mem0 Layer - Cross-session user persona with vector-based semantic search
class UserMemory(Base):
    __tablename__ = "user_memories"
    
    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    memory_text = Column(Text, nullable=False)
    embedding = Column(Vector(1536))  # pgvector
    memory_type = Column(String(50), default="conversation")
    meta_data = Column(JSONB, default={})
    relevance_score = Column(Float, default=1.0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="memories")
    
    # Vector similarity index (HNSW for fast approximate search) and standard indexes
    __table_args__ = (
        Index('idx_memories_embedding', 'embedding', 
              postgresql_using='hnsw', 
              postgresql_with={'m': 16, 'ef_construction': 64},
              postgresql_ops={'embedding': 'vector_cosine_ops'}),
        Index('idx_memories_user_type', 'user_id', 'memory_type'),
        Index('idx_memories_created', 'created_at', postgresql_using='btree', postgresql_ops={'created_at': 'DESC'}),
        Index('idx_memories_meta_data', 'meta_data', postgresql_using='gin'),
    )

# Mem0 Layer - Cross-session user persona with vector-based semantic search
class UserFact(Base):
    __tablename__ = "user_facts"
    
    fact_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False)
    fact_key = Column(String(255), nullable=False)
    fact_value = Column(JSONB, nullable=False)
    confidence_score = Column(Integer, CheckConstraint("confidence_score BETWEEN 0 AND 100"))
    source_memory_id = Column(UUID(as_uuid=True), ForeignKey("user_memories.memory_id", ondelete="SET NULL"))
    first_mentioned = Column(DateTime(timezone=True), default=datetime.utcnow)
    last_updated = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="facts")
    
    # Indexes for fact lookups
    __table_args__ = (
        Index('idx_facts_user_category', 'user_id', 'category'),
        Index('idx_facts_updated', 'last_updated', postgresql_using='btree', postgresql_ops={'last_updated': 'DESC'}),
        Index('idx_facts_value', 'fact_value', postgresql_using='gin'),
    )