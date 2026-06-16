from livekit.agents import function_tool, RunContext

from src.agents.indusnet.constants import TOPIC_UI_RICH_CARD


class RichCardToolsMixin:
    """Tool for publishing a rich TEXT card to the user's screen.

    A rich text card carries NO images — that is the job of the UI image card
    ('publish_ui_stream'). It is for text-heavy answers that deserve fuller,
    well-structured text than a terse image flashcard: pricing, process,
    explainers, partners, comparisons, greetings, and general replies. The main
    agent LLM authors the content directly; the frontend renders the title,
    markdown body, bullets, chips, and header icon.
    """

    @function_tool
    async def publish_rich_card(
        self,
        context: RunContext,
        title: str,
        markdown_content: str,
        bullets: list[str] | None = None,
        chips: list[str] | None = None,
        visual_intent: str = "neutral",
        icon: str = "info",
    ) -> str:
        """
        Render a polished rich TEXT card on the user's screen. NO images — this card
        is text-only; use 'publish_ui_stream' when the topic warrants image flashcards
        (see ui_publishing_policy). A rich text card can hold MORE and LONGER structured
        text than a UI image card.

        Do NOT call this when 'publish_ui_stream' or any dedicated screen tool
        (publisg_gloabl_pesense, publish_nearby_offices, publish_office_details,
        preview_contact_form, preview_job_application, preview_meeting_invite,
        calculate_distance_to_destination) is already being called this turn — pick
        ONE visual per turn. The markdown is rendered visually only; your SPOKEN reply
        must stay plain prose. IMPORTANT: this REPLACES everything currently on screen.

        Args:
            title: A short, scannable headline (3-8 words).
            markdown_content: The card body as rich markdown (paragraphs, **bold**).
                Can be richer and longer than a UI image card's terse bullets.
            bullets: Optional short feature/checklist items rendered as a checked list.
            chips: Optional tag pills shown at the foot of the card (e.g. industries).
            visual_intent: Card style — neutral|urgent|success|warning|processing.
            icon: A Lucide icon name for the card header (e.g. info, sparkles, user, phone).
        """
        self.logger.info(f"Publishing rich text card to the UI: {title}")

        payload = {
            "type": "rich_card",
            "title": title,
            "content": markdown_content,
            "bullets": bullets or [],
            "chips": chips or [],
            "visual_intent": visual_intent,
            "icon": icon,
        }

        await self._publish_data_packet(payload, TOPIC_UI_RICH_CARD)
        self._set_last_ui_snapshot(
            snapshot_type="rich_card",
            title=title,
            summary=markdown_content[:120],
            details=payload,
            source_tool="publish_rich_card",
        )

        return "Rich text card published to the screen."
