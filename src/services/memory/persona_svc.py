from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from src.api.models.db_schemas import UserMemory, UserFact
from src.core.logger import get_logger

logger = get_logger(__name__)

class PersonaService:
    """
    Mem0 Layer: Cross-session semantic memory.
    Handles vector memories and structured user facts.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== USER MEMORY (VECTOR) ====================
    
    async def add_user_memory(
        self,
        user_id: uuid.UUID,
        memory_text: str,
        embedding: List[float],
        memory_type: str = "conversation",
        meta_data: Optional[Dict[str, Any]] = None,
        relevance_score: float = 1.0
    ) -> UserMemory:
        """Add semantic memory with vector embedding."""
        memory = UserMemory(
            user_id=user_id,
            memory_text=memory_text,
            embedding=embedding,
            memory_type=memory_type,
            meta_data=meta_data or {},
            relevance_score=relevance_score
        )
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        logger.info(f"Added memory {memory.memory_id} for user {user_id}")
        return memory
    
    async def search_memories(
        self,
        user_id: uuid.UUID,
        query_embedding: List[float],
        limit: int = 5,
        threshold: float = 0.7,
        memory_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search user memories using vector similarity.
        Returns memories with similarity scores.
        """
        # Build query with pgvector cosine distance
        # Note: Using 1 - cosine_distance to get similarity (higher = more similar)
        # We need to access the embedding column properly
        similarity = (1 - UserMemory.embedding.cosine_distance(query_embedding)).label('similarity')
        
        query = select(UserMemory, similarity).where(UserMemory.user_id == user_id)
        
        if memory_type:
            query = query.where(UserMemory.memory_type == memory_type)
        
        # Filter by threshold and order by similarity
        query = (
            query
            .where(similarity >= threshold)
            .order_by(desc('similarity'))
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                'memory': row[0],
                'similarity': float(row[1])
            }
            for row in rows
        ]
    
    async def get_recent_memories(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
        memory_type: Optional[str] = None
    ) -> List[UserMemory]:
        """Get user's most recent memories."""
        query = (
            select(UserMemory)
            .where(UserMemory.user_id == user_id)
        )
        
        if memory_type:
            query = query.where(UserMemory.memory_type == memory_type)
        
        query = query.order_by(desc(UserMemory.created_at)).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def update_memory_relevance(
        self,
        memory_id: uuid.UUID,
        relevance_score: float
    ) -> UserMemory:
        """Update memory relevance score."""
        result = await self.db.execute(
            select(UserMemory).where(UserMemory.memory_id == memory_id)
        )
        memory = result.scalar_one()
        memory.relevance_score = relevance_score
        memory.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(memory)
        return memory
    
    # ==================== USER FACTS (STRUCTURED) ====================
    
    async def add_user_fact(
        self,
        user_id: uuid.UUID,
        category: str,
        fact_key: str,
        fact_value: Dict[str, Any],
        confidence_score: int,
        source_memory_id: Optional[uuid.UUID] = None
    ) -> UserFact:
        """Add or update a structured user fact."""
        # Check if fact already exists
        result = await self.db.execute(
            select(UserFact).where(
                and_(
                    UserFact.user_id == user_id,
                    UserFact.category == category,
                    UserFact.fact_key == fact_key
                )
            )
        )
        existing_fact = result.scalar_one_or_none()
        
        if existing_fact:
            # Update existing fact
            existing_fact.fact_value = fact_value
            existing_fact.confidence_score = confidence_score
            existing_fact.last_updated = datetime.utcnow()
            if source_memory_id:
                existing_fact.source_memory_id = source_memory_id
            await self.db.commit()
            await self.db.refresh(existing_fact)
            logger.info(f"Updated fact {existing_fact.fact_id}")
            return existing_fact
        
        # Create new fact
        fact = UserFact(
            user_id=user_id,
            category=category,
            fact_key=fact_key,
            fact_value=fact_value,
            confidence_score=confidence_score,
            source_memory_id=source_memory_id
        )
        self.db.add(fact)
        await self.db.commit()
        await self.db.refresh(fact)
        logger.info(f"Added fact {fact.fact_id} for user {user_id}")
        return fact
    
    async def get_user_facts(
        self,
        user_id: uuid.UUID,
        category: Optional[str] = None
    ) -> List[UserFact]:
        """Get user facts, optionally filtered by category."""
        query = select(UserFact).where(UserFact.user_id == user_id)
        
        if category:
            query = query.where(UserFact.category == category)
        
        query = query.order_by(desc(UserFact.last_updated))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_fact_by_key(
        self,
        user_id: uuid.UUID,
        category: str,
        fact_key: str
    ) -> Optional[UserFact]:
        """Get a specific fact by category and key."""
        result = await self.db.execute(
            select(UserFact).where(
                and_(
                    UserFact.user_id == user_id,
                    UserFact.category == category,
                    UserFact.fact_key == fact_key
                )
            )
        )
        return result.scalar_one_or_none()
