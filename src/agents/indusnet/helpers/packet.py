import json
from typing import Optional

from livekit import rtc


class PacketHelperMixin:
    """Low-level helpers for reading and writing LiveKit data packets."""

    def _extract_payload_text(self, data: rtc.DataPacket) -> Optional[str]:
        """Extract and decode payload text from data packet."""
        payload = getattr(data, "data", None)
        if isinstance(payload, bytes):
            return payload.decode("utf-8", errors="ignore")
        return str(payload) if payload is not None else None

    async def _publish_data_packet(self, payload: dict, topic: str) -> bool:
        """Publish a single data packet to the room."""
        try:
            await self.room.local_participant.publish_data(
                json.dumps(payload, default=str).encode("utf-8"),
                reliable=True,
                topic=topic,
            )
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to publish data: {e}")
            return False
