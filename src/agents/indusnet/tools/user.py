from livekit.agents import function_tool, RunContext


class UserToolsMixin:
    """Tool for capturing and syncing user identity information."""

    @function_tool
    async def get_user_info(
        self,
        context: RunContext,
        user_name: str,
        user_email: str = "",
        user_phone: str = "",
    ):
        """Get user information."""
        self.logger.info(f"Retrieving user information for: {user_name}")

        # Publish user information via data packet
        payload = {
            "user_name": user_name,
            "user_email": user_email,
            "user_phone": user_phone,
            "user_id": self.user_id,
        }
        topic = "user.details"
        await self._publish_data_packet(payload, topic)
        return "User information published."
