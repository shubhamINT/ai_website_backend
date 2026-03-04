import asyncio
import datetime as dt

from livekit.agents import function_tool, RunContext

from src.services.mail.calender_invite import send_calendar_invite


class MeetingToolsMixin:
    """Tool for scheduling meetings and sending calendar invites."""

    @function_tool
    async def schedule_meeting(
        self,
        context: RunContext,
        recipient_email: str,
        subject: str,
        description: str,
        location: str,
        start_time_iso: str,
        duration_hours: float = 1.0,
    ):
        """
        Schedule a meeting and send a calendar invite.

        Args:
            recipient_email: The email address to send the invite to.
            subject: The title of the meeting.
            description: A brief description of the meeting.
            location: Where the meeting will happen (e.g., 'Zoom', 'Office').
            start_time_iso: The start time in ISO 8601 format (e.g., '2026-02-21T14:00:00').
            duration_hours: How long the meeting lasts in hours (default: 1.0).
        """
        self.logger.info(f"Scheduling meeting for {recipient_email}: {subject}")

        try:
            start_time = dt.datetime.fromisoformat(start_time_iso)
        except ValueError:
            return "Invalid date format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)."

        # Run the blocking send_calendar_invite in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(
            None,
            send_calendar_invite,
            recipient_email,
            subject,
            description,
            location,
            start_time,
            duration_hours,
        )

        if success:
            return (
                f"Meeting '{subject}' scheduled and invite sent to {recipient_email}."
            )
        else:
            return f"Failed to send the meeting invite. Please check the logs."
