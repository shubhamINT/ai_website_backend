from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from src.api.models.db_schemas import User
from src.core.logger import get_logger
from src.services.memory.session_svc import SessionService
from src.services.memory.persona_svc import PersonaService

logger = get_logger(__name__)

class DualLayerService:
    """
    Unified interface for determining memory architecture.
    Combines Session (Zep) and Persona (Mem0) layers.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_svc = SessionService(db)
        self.persona_svc = PersonaService(db)
        
    # ==================== USER MANAGEMENT ====================
    
    async def get_or_create_user(
        self, 
        email: str, 
        name: Optional[str] = None,
        meta_data: Optional[Dict[str, Any]] = None
    ) -> User:
        """Get existing user or create new one."""
        # Try to find existing user
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update last_active
            user.last_active = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(user)
            logger.info(f"Found existing user: {user.user_id}")
            return user
        
        # Create new user
        user = User(
            email=email,
            name=name,
            meta_data=meta_data or {}
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"Created new user: {user.user_id}")
        return user
    
    async def update_user_metadata(
        self, 
        user_id: uuid.UUID, 
        meta_data: Dict[str, Any]
    ) -> User:
        """Update user metadata."""
        result = await self.db.execute(
            select(User).where(User.user_id == user_id)
        )
        user = result.scalar_one()
        user.meta_data = meta_data
        user.last_active = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    # ==================== UNIFIED OPERATIONS ====================

    async def start_conversation(
        self,
        user_id: uuid.UUID,
        session_type: str = "conversation",
        meta_data: Optional[Dict[str, Any]] = None
    ) -> uuid.UUID:
        """
        Start a new conversation session.
        Wrapper around session_svc.create_session.
        """
        session = await self.session_svc.create_session(
            user_id=user_id,
            session_type=session_type,
            meta_data=meta_data
        )
        return session.session_id

    async def process_turn(
        self,
        session_id: uuid.UUID,
        user_message: str,
        assistant_message: str,
        turn_number: int,
        ui_cards: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Process a full conversation turn:
        1. store user message
        2. store assistant message
        3. store UI cards
        """
        # Store user message
        await self.session_svc.add_message(
            session_id=session_id,
            turn_number=turn_number,
            role='user',
            content=user_message
        )
        
        # Store assistant message (same turn? or next sequence logic handled by caller?)
        # Convention: Messages in same turn usually share turn_number, but role differs.
        # Or message ID orders them. 
        # The schema has turn_number + role. 
        # Usually user requests -> turn N. Assistant replies -> turn N (or N+1?).
        # Zep usually groups by turn. Let's assume same turn number for the pair.
        
        await self.session_svc.add_message(
            session_id=session_id,
            turn_number=turn_number,
            role='assistant',
            content=assistant_message
        )
        
        # Store UI cards if any
        if ui_cards:
            for i, card in enumerate(ui_cards):
                await self.session_svc.add_ui_card(
                    session_id=session_id,
                    turn_number=turn_number,
                    card_type=card.get('type', 'unknown'),
                    card_data=card,
                    display_order=i
                )

    async def build_conversation_context(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        current_query: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        max_history_messages: int = 10,
        max_memories: int = 5
    ) -> Dict[str, Any]:
        """
        Build complete context for agent including:
        - Recent session messages
        - Relevant semantic memories
        - User facts
        """
        # Get recent conversation history from Session Layer
        recent_messages = await self.session_svc.get_recent_messages(
            session_id=session_id,
            limit=max_history_messages
        )
        
        # Get relevant memories from Persona Layer if query embedding provided
        relevant_memories = []
        if query_embedding:
            memory_results = await self.persona_svc.search_memories(
                user_id=user_id,
                query_embedding=query_embedding,
                limit=max_memories,
                threshold=0.7
            )
            relevant_memories = [m['memory'] for m in memory_results]
        
        # Get user facts from Persona Layer
        user_facts = await self.persona_svc.get_user_facts(user_id=user_id)
        
        return {
            'recent_messages': recent_messages,
            'relevant_memories': relevant_memories,
            'user_facts': user_facts,
            'current_query': current_query
        }
