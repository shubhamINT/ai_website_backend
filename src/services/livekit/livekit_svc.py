import uuid
import json
import logging
from typing import List, Optional
from livekit.api import LiveKitAPI, ListRoomsRequest
from livekit import api as lk_api
from src.core.config import settings

logger = logging.getLogger(__name__)

class LiveKitService:
    def __init__(self):
        self.api_key = settings.LIVEKIT_API_KEY
        self.api_secret = settings.LIVEKIT_API_SECRET
        self.url = settings.LIVEKIT_URL

    async def get_rooms(self) -> List[str]:
        client = LiveKitAPI()
        try:
            rooms = await client.room.list_rooms(ListRoomsRequest())
            return [room.name for room in rooms.rooms]
        except Exception as e:
            logger.error(f"Error listing rooms: {e}")
            return []
        finally:
            await client.aclose()

    async def generate_room_name(self, agent: str) -> str:
        while True:
            room_name = f"{agent}-{uuid.uuid4().hex[:8]}"
            existing_rooms = await self.get_rooms()
            if room_name not in existing_rooms:
                return room_name

    def get_token(self, identity: str, agent: str, room: Optional[str] = None) -> str:
        token = (
            lk_api.AccessToken(self.api_key, self.api_secret)
            .with_identity(identity)
            .with_name(identity)
            .with_metadata(json.dumps({"agent": agent}))
            .with_grants(
                lk_api.VideoGrants(
                    room_join=True,
                    room=room,
                )
            )
        )
        return token.to_jwt()

livekit_service = LiveKitService()
