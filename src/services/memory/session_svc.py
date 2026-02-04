from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from src.api.models.db_schemas import Session, SessionMessage, UICardShown
from src.core.logger import get_logger

logger = get_logger(__name__)

class SessionService:
    """
    Zep Layer: Session & message management.
    Handles conversation sessions, messages, and UI card tracking.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # ==================== SESSION MANAGEMENT ====================
    
    async def create_session(
        self,
        user_id: uuid.UUID,
        session_type: str = "conversation",
        meta_data: Optional[Dict[str, Any]] = None
    ) -> Session:
        """Create a new conversation session."""
        session = Session(
            user_id=user_id,
            session_type=session_type,
            meta_data=meta_data or {},
            is_active=True
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        logger.info(f"Created session {session.session_id} for user {user_id}")
        return session
    
    async def get_active_session(self, user_id: uuid.UUID) -> Optional[Session]:
        """Get the currently active session for a user."""
        result = await self.db.execute(
            select(Session)
            .where(
                and_(
                    Session.user_id == user_id,
                    Session.is_active == True
                )
            )
            .order_by(desc(Session.started_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def end_session(self, session_id: uuid.UUID) -> Session:
        """Mark a session as ended."""
        result = await self.db.execute(
            select(Session).where(Session.session_id == session_id)
        )
        session = result.scalar_one()
        session.is_active = False
        session.ended_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(session)
        logger.info(f"Ended session {session_id}")
        return session
    
    async def get_user_sessions(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
        skip: int = 0
    ) -> List[Session]:
        """Get user's session history."""
        result = await self.db.execute(
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(desc(Session.started_at))
            .limit(limit)
            .offset(skip)
        )
        return list(result.scalars().all())
    
    # ==================== MESSAGE MANAGEMENT ====================
    
    async def add_message(
        self,
        session_id: uuid.UUID,
        turn_number: int,
        role: str,
        content: str,
        meta_data: Optional[Dict[str, Any]] = None
    ) -> SessionMessage:
        """Add a message to the conversation history."""
        message = SessionMessage(
            session_id=session_id,
            turn_number=turn_number,
            role=role,
            content=content,
            meta_data=meta_data or {}
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        logger.debug(f"Added message {message.message_id} to session {session_id}")
        return message
    
    async def get_session_messages(
        self,
        session_id: uuid.UUID,
        limit: Optional[int] = None
    ) -> List[SessionMessage]:
        """Get all messages from a session, ordered by turn number."""
        query = (
            select(SessionMessage)
            .where(SessionMessage.session_id == session_id)
            .order_by(SessionMessage.turn_number, SessionMessage.created_at)
        )
        
        if limit:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_recent_messages(
        self,
        session_id: uuid.UUID,
        limit: int = 10
    ) -> List[SessionMessage]:
        """Get the N most recent messages from a session."""
        result = await self.db.execute(
            select(SessionMessage)
            .where(SessionMessage.session_id == session_id)
            .order_by(desc(SessionMessage.turn_number), desc(SessionMessage.created_at))
            .limit(limit)
        )
        # Reverse to get chronological order
        messages = list(result.scalars().all())
        return messages[::-1]
    
    async def get_messages_by_turn(
        self,
        session_id: uuid.UUID,
        turn_number: int
    ) -> List[SessionMessage]:
        """Get all messages from a specific turn."""
        result = await self.db.execute(
            select(SessionMessage)
            .where(
                and_(
                    SessionMessage.session_id == session_id,
                    SessionMessage.turn_number == turn_number
                )
            )
            .order_by(SessionMessage.created_at)
        )
        return list(result.scalars().all())
    
    # ==================== UI CARD TRACKING ====================
    
    async def add_ui_card(
        self,
        session_id: uuid.UUID,
        turn_number: int,
        card_type: str,
        card_data: Dict[str, Any],
        display_order: int
    ) -> UICardShown:
        """Track UI cards shown during conversation."""
        ui_card = UICardShown(
            session_id=session_id,
            turn_number=turn_number,
            card_type=card_type,
            card_data=card_data,
            display_order=display_order
        )
        self.db.add(ui_card)
        await self.db.commit()
        await self.db.refresh(ui_card)
        logger.debug(f"Added UI card {card_type} to session {session_id}")
        return ui_card
    
    async def get_ui_cards_for_turn(
        self,
        session_id: uuid.UUID,
        turn_number: int
    ) -> List[UICardShown]:
        """Get all UI cards shown at a specific turn."""
        result = await self.db.execute(
            select(UICardShown)
            .where(
                and_(
                    UICardShown.session_id == session_id,
                    UICardShown.turn_number == turn_number
                )
            )
            .order_by(UICardShown.display_order)
        )
        return list(result.scalars().all())
