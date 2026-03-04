import asyncio
from typing import Optional


class AgentState:
    """
    Holds all mutable runtime state for the IndusNetAgent.

    Separating state from behavior keeps __init__ lean and makes
    state fields easy to find, document, and reset if needed.
    """

    def _init_state(self) -> None:
        """Initialise all state fields. Call this from IndusNetAgent.__init__."""

        # ── Vector DB ──────────────────────────────────────────────
        self.db_fetch_size: int = 10
        self.db_results: str = ""

        # ── User Context ───────────────────────────────────────────
        self.user_id: Optional[str] = None
        self.user_name: Optional[str] = None
        self.user_email: Optional[str] = None
        self.user_phone: Optional[str] = None

        # ── UI Context ─────────────────────────────────────────────
        self._active_elements: list[str] = []

        # ── Location State ─────────────────────────────────────────
        self._location_status: Optional[str] = None  # "success" | "denied" | "unsupported"
        self._user_lat: Optional[float] = None
        self._user_lng: Optional[float] = None
        self._user_address: Optional[str] = None
        self._location_accuracy: Optional[float] = None
        self._location_event: asyncio.Event = asyncio.Event()  # fired when frontend responds
