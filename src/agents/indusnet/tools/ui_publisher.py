import asyncio
import re
import uuid

from livekit.agents import function_tool, RunContext
from pydantic import BaseModel

from src.agents.indusnet.constants import (
    TOPIC_UI_FLASHCARD,
    TOPIC_GLOBAL_PRESENCE,
    TOPIC_NEARBY_OFFICES,
    TOPIC_OFFICE_DETAILS,
    TOPIC_UI_NAVIGATE,
)

# Navigation confidence thresholds, calibrated against the page_index re-ranking
# (cosine similarity + a small boost for primary/structural pages — see
# ScrapNinja's scrapninja/load/build_page_index.py). score is in roughly [0, 1.2].
_NAV_PRIORITY_WEIGHT = 0.10   # boost per nav_priority point
_NAV_MEDIUM_SCORE = 0.30      # below this → don't navigate, ask the user


def _nav_is_high_confidence(score: float, margin: float) -> bool:
    """A clear winner: either a strong score with a real gap to #2, or a
    moderate score that dominates the runner-up."""
    return (score >= 0.45 and margin >= 0.05) or (score >= 0.35 and margin >= 0.20)


class Office(BaseModel):
    """A single Indus Net office location, copied verbatim from OFFICE_DATA."""

    id: str
    name: str
    address: str
    lat: float
    lng: float
    image_url: str


class UIPublisherToolsMixin:
    """Tools for publishing UI content (flashcards, global presence, nearby offices, office details) to the frontend."""

    def _build_knowledge_email_context(
        self,
        user_input: str,
        agent_response: str,
    ) -> dict:
        topic_hint = (user_input or "").strip()
        topic_hint = re.sub(r"^(hi|hello|hey)\s+", "", topic_hint, flags=re.IGNORECASE)
        topic_hint = re.sub(
            r"^(can you|could you|please|tell me about|what about|what is|who is|show me|explain)\s+",
            "",
            topic_hint,
            flags=re.IGNORECASE,
        )
        topic_hint = topic_hint.strip(" ?!.,:")
        if len(topic_hint) > 60:
            topic_hint = ""

        return {
            "email_type": "knowledge_summary",
            "topic_hint": topic_hint,
            "raw_summary": agent_response,
            "context_line": "Key information from Indus Net Assistant.",
        }

    @function_tool
    async def publish_ui_stream(
        self,
        context: RunContext,
        user_input: str,
        agent_response: str,
        navigate_to: str = "",
    ) -> str:
        """Tool used to publish the UI stream to the frontend.

        Args:
            user_input: The user's original query.
            agent_response: Your curated, consultant-level summary to turn into cards.
            navigate_to: Optional. Set this ONLY when the user asked, in the SAME
                request, to BOTH learn about a topic AND be taken to its page
                (e.g. "tell me about your products and take me to the product
                page"). Pass a concise description of the page they want to open
                (e.g. "products"). The cards are shown and narrated FIRST, then the
                page opens, then the redirect is announced — all timed for you.
                Leave empty for a normal "just explain it" request.
        """
        self.logger.info(f"Publishing UI stream for: {user_input}")

        self._set_last_ui_snapshot(
            snapshot_type="flashcard_stream",
            title="Knowledge summary",
            summary=agent_response,
            details={"user_input": user_input},
            source_tool="publish_ui_stream",
            email_context=self._build_knowledge_email_context(
                user_input, agent_response
            ),
        )

        # Run in the background. Pass session so each card can be narrated
        # via session.say() in sync with its appearance on screen.
        asyncio.create_task(
            self._publish_ui_stream(
                user_input, self.db_results, agent_response, self.user_id,
                session=context.session,
                navigate_to=navigate_to,
            )
        )
        return "UI stream published."

    @function_tool
    async def recall_and_republish_ui_content(
        self, context: RunContext, agent_response: str
    ) -> str:
        """
        Recall and re-publish a previously displayed UI flashcard set from memory.
        Use this when the user asks to go back, see previous content, or revisit
        a topic that was already shown on screen.

        Args:
            agent_response: A short description of the content the user wants to see again,
                   interpreted by you based on user intent (e.g. 'services').
        """
        self.logger.info("🔁 Recall UI content requested for: '%s'", agent_response)

        if not self.user_id:
            return (
                "I don't have your user information yet, so I can't retrieve "
                "your previous session content. Could you please introduce yourself?"
            )

        cards = await self.ui_agent_functions.recall_ui_content(
            agent_response=agent_response, user_id=self.user_id
        )

        if not cards:
            return (
                f"I couldn't find any previously shown content matching '{agent_response}'. "
                "Would you like me to fetch that information fresh for you?"
            )

        # Re-publish the exact same cards from memory
        stream_id = str(uuid.uuid4())
        for card_index, card in enumerate(cards):
            card["stream_id"] = stream_id
            card["card_index"] = card_index
            card["recalled"] = True  # flag so frontend knows it's a replay
            await self._publish_data_packet(card, TOPIC_UI_FLASHCARD)

        # End-of-stream marker
        await self._publish_data_packet(
            {
                "type": "end_of_stream",
                "stream_id": stream_id,
                "card_count": len(cards),
            },
            TOPIC_UI_FLASHCARD,
        )

        self.logger.info(
            "✅ Re-published %d recalled flashcard(s) for user %s",
            len(cards),
            self.user_id,
        )
        self._set_last_ui_snapshot(
            snapshot_type="flashcard_recall",
            title="Recalled content",
            summary=f"Re-displayed {len(cards)} flashcard(s) from previous session content.",
            details={"query": agent_response, "card_count": len(cards)},
            source_tool="recall_and_republish_ui_content",
        )
        return f"Re-displayed {len(cards)} flashcard(s) from your previous session."

    @function_tool
    async def publish_global_presence(
        self, context: RunContext, user_input: str = "global presence"
    ) -> str:
        """Publish Indus Net global presence details via data packet."""
        self.logger.info("Publishing global presence details via data packet")

        payload = {
            "type": "global_presence",
            "data": {
                "regions": {
                    "USA": "1310 S Vista Ave Ste 28, Boise, Idaho – 83705",
                    "Canada": "120 Adelaide Street West, Suite 2500, M5H 1T1",
                    "UK": "13 More London Riverside, London SE1 2RE",
                    "Poland": "BARTYCKA 22B M21A, 00-716 WARSZAWA",
                    "Singapore": "Indus Net Technologies PTE Ltd., 60 Paya Lebar Road, #09-43 Paya Lebar Square – 409051",
                },
                "headquarters": {
                    "Kolkata Newtown (Headquarters)": "4th Floor, Block-2b, ECOSPACE BUSINESS PARK, AA II, Newtown, Chakpachuria, West Bengal 700160",
                    "Kolkata Sector 5": "4th Floor, SDF Building Saltlake Electronic Complex, Kolkata, West Bengal 700091",
                },
            },
        }

        await self._publish_data_packet(payload, TOPIC_GLOBAL_PRESENCE)
        self._set_last_ui_snapshot(
            snapshot_type="global_presence",
            title="Global presence",
            summary="Displayed Indus Net global and headquarters locations.",
            details=payload.get("data", {}),
            source_tool="publish_global_presence",
        )
        return "Global presence data published."


    @function_tool
    async def publish_nearby_offices(self, context: RunContext, offices: list[Office]) -> str:
        """
        Publish the Indus Net offices nearest to the user on the UI.

        Pick the 1–3 closest offices from OFFICE_DATA in your system instructions
        and pass them as the `offices` list. Each office object must be copied
        verbatim from OFFICE_DATA (do NOT invent fields).

        Always ask for the user's location before calling this tool if unknown.
        Do NOT call this tool with an empty list or without the 'offices' argument.

        Example call:
            offices=[
                {
                    "id": "kolkata-sector-5",
                    "name": "Kolkata Sector 5 (SDF Building)",
                    "address": "4th Floor, SDF Building Saltlake Electronic Complex, Kolkata, West Bengal 700091",
                    "lat": 22.5726,
                    "lng": 88.4312,
                    "image_url": "https://intglobal.com/wp-content/uploads/2025/06/image-134.webp"
                }
            ]

        Args:
            offices: List of 1–3 office objects copied directly from OFFICE_DATA.
                     Must include: id, name, address, lat, lng, image_url.
        """
        if not offices:
            return "No offices provided."

        self.logger.info(f"Publishing {len(offices)} nearby office(s)")

        # Serialize Pydantic models to plain dicts for the frontend data packet
        office_dicts = [office.model_dump() for office in offices]
        payload = {
            "type": "nearby_offices",
            "data": {"offices": office_dicts},
        }

        await self._publish_data_packet(payload, TOPIC_NEARBY_OFFICES)
        self._set_last_ui_snapshot(
            snapshot_type="nearby_offices",
            title="Nearby offices",
            summary=f"Displayed {len(offices)} nearby Indus Net office location(s).",
            details=payload.get("data", {}),
            source_tool="publish_nearby_offices",
        )
        return f"Published {len(offices)} nearby office(s) to the UI."

    @function_tool
    async def publish_office_details(self, context: RunContext, office: Office) -> str:
        """
        Publish ONE specific Indus Net office in detail on the user's screen.

        Use this when the user wants to SEE a particular office (e.g. "show me
        the Newtown office", "tell me about the Singapore office", or after they
        pick one from the nearby-offices or global-presence view). Pass the
        single office object copied verbatim from OFFICE_DATA — id, name,
        address, lat, lng, image_url.

        For 1–3 closest offices use 'publish_nearby_offices' instead. This tool
        is for a single, specific office.

        IMPORTANT: Calling this tool REPLACES everything currently on the
        user's screen.

        Args:
            office: One office object copied directly from OFFICE_DATA.
                    Must include: id, name, address, lat, lng, image_url.
        """
        self.logger.info("Publishing office details for: %s", office.name)

        payload = {
            "type": "office_details",
            "data": {"office": office.model_dump()},
        }

        await self._publish_data_packet(payload, TOPIC_OFFICE_DETAILS)
        self._set_last_ui_snapshot(
            snapshot_type="office_details",
            title=f"Office: {office.name}",
            summary=f"Displayed details for {office.name} ({office.address}).",
            details=payload.get("data", {}),
            source_tool="publish_office_details",
        )
        return f"Published details for {office.name} to the UI."

    @function_tool
    async def get_current_page(self, context: RunContext) -> str:
        """
        Return the website page the user is CURRENTLY viewing, live.

        Call this whenever the user asks what page or screen they are on, where
        they are on the site, or anything similar. ALWAYS trust this result over
        anything said earlier in the conversation — the user may have navigated
        using the website's own links (e.g. a 'Back to home' button) without
        telling you, so your memory of the page can be stale.
        """
        labels = {"/products": "Products", "/vani": "Home", "/": "Home"}
        page = self._current_page
        if not page:
            return "The user is on the Home page (no navigation has happened yet this session)."
        if page in labels:
            label = labels[page]
        else:
            # Humanise the last path segment, e.g. "/services/ai-model" → "Ai Model".
            segs = [s for s in page.split("/") if s]
            label = segs[-1].replace("-", " ").replace("_", " ").title() if segs else "Home"
        return f"The user is currently on the {label} page ({page})."

    @function_tool
    async def navigate_to_page(self, context: RunContext, query: str) -> str:
        """
        Open a website page in the user's browser WITHOUT disturbing this chat —
        the conversation, this window, and your session stay intact.

        Use this ONLY when the user explicitly asks to GO somewhere on the site
        (e.g. "take me to the products page", "open your services page", "show me
        the page about your CEO", "go to careers", "open the Bandhan Bank case
        study"). Do NOT use it just because the user asked ABOUT a topic — that is
        a 'publish_ui_stream' (cards) job, not navigation.

        This searches a knowledge base of all ~950 website pages and resolves the
        best match. On a confident match it navigates immediately. If it's unsure,
        it returns the top candidates — read them back and ask the user which one
        they meant, then call this tool again with their choice.

        Args:
            query: A concise description of the page the user wants, in your own
                words (e.g. "products", "AI development services", "about the
                company / CEO", "partners", "banking & finance industry").
        """
        res = await self._resolve_navigation(query)
        if res is None:
            return "I couldn't look up the site pages just now — please try again in a moment."
        if res["status"] == "none":
            return (
                "I couldn't find a matching page. Could you tell me the section — "
                "for example products, services, industries, about, or contact?"
            )

        if res["status"] == "high":
            await self._do_navigate(res["url"], res["path"], res["title"])
            # Speech behaviour (one short confirmation, then STOP — no follow-up)
            # is enforced by the 'Page Navigation' prompt rule.
            return f"Navigated to the {res['title']} page."

        if res["status"] == "medium":
            options = ", ".join(f"'{c}'" for c in res["candidates"])
            self.logger.info("🧭 navigate ambiguous -> %s", options)
            return (
                f"I'm not fully sure which page you want. Did you mean one of these: "
                f"{options}? Ask the user to pick, then call navigate_to_page again "
                f"with their choice. Do NOT navigate yet."
            )

        self.logger.info("🧭 navigate no confident match (top=%.2f)", res["score"])
        return (
            "I couldn't confidently match a page to that. Ask the user to name the "
            "section (e.g. products, services, industries, about, partners, contact). "
            "Do NOT navigate yet."
        )

    async def _resolve_navigation(self, query: str) -> dict | None:
        """Resolve a free-text page request against the page_index.

        Returns a dict with status ('high' | 'medium' | 'low' | 'none'), the best
        url/path/title, and the top candidate titles — or None if the search
        itself failed. Shared by navigate_to_page and the post-cards navigation
        in _publish_ui_stream so both rank and threshold identically.
        """
        q = (query or "").strip()
        if not q:
            return {"status": "none", "score": 0.0, "candidates": []}
        try:
            results = await self.vector_store.search_pages(q, k=10)
        except Exception as e:
            self.logger.error("_resolve_navigation: page search failed: %s", e)
            return None
        if not results:
            return {"status": "none", "score": 0.0, "candidates": []}

        def _cos(dist: float) -> float:
            return max(0.0, min(1.0, 1 - (dist * dist) / 2))

        ranked = sorted(
            (
                {
                    "meta": doc.metadata,
                    "score": _cos(dist)
                    + _NAV_PRIORITY_WEIGHT * float(doc.metadata.get("nav_priority", 1) or 0),
                }
                for doc, dist in results
            ),
            key=lambda r: r["score"],
            reverse=True,
        )
        top = ranked[0]
        margin = top["score"] - (ranked[1]["score"] if len(ranked) > 1 else 0.0)
        meta = top["meta"]

        if _nav_is_high_confidence(top["score"], margin):
            status = "high"
        elif top["score"] >= _NAV_MEDIUM_SCORE:
            status = "medium"
        else:
            status = "low"

        return {
            "status": status,
            "score": top["score"],
            "margin": margin,
            "url": meta.get("url"),
            "path": meta.get("path"),
            "title": meta.get("title") or meta.get("path") or "that",
            "candidates": [
                r["meta"].get("title") for r in ranked[:3] if r["meta"].get("title")
            ],
        }

    async def _do_navigate(self, url: str, path: str, title: str) -> None:
        """Publish the navigate packet and become aware of the new page
        immediately (don't wait for the frontend's ui.context to round-trip)."""
        await self._publish_data_packet(
            {"type": "navigate", "url": url, "path": path, "title": title},
            TOPIC_UI_NAVIGATE,
        )
        self._current_page = path
        await self._update_instructions()
        self.logger.info("🧭 navigate -> %s", path)

    @function_tool
    async def get_ui_history(self, context: RunContext) -> str:
        """
        Return the list of screens shown this session in order (oldest → newest).
        The current screen is marked with *.
        Call this BEFORE any back-navigation action to get the real server-tracked history.
        """
        titles = self._get_snapshot_history_titles()
        if not titles:
            return "No screen history yet this session."
        return "\n".join(titles)

    async def _publish_ui_stream(
        self,
        user_input: str,
        db_results: str,
        agent_response: str,
        user_id: str,
        session=None,
        navigate_to: str = "",
    ) -> None:
        """Three-phase card publishing with per-card TTS sync.

        Phase 1 — Collect:  GPT-4o-mini streams all cards into memory. No
                            publishing yet; the main LLM's brief intro plays
                            naturally during this time.

        Phase 2 — Narrate:  For each card, publish it with a UNIQUE stream_id
                            (the frontend clears the previous card on stream_id
                            change) then await session.say(narration). User sees
                            exactly ONE card while its narration plays. Blocking
                            is fine here because all cards are already collected.

        Phase 3 — Browse:   Republish all cards under a shared final stream_id
                            so the CardStack appears and the user can navigate.
                            Follow-up question restarts the silence watchdog.
        """
        base_stream_id = str(uuid.uuid4())

        # No separate transition phrase is spoken before the cards. The agent's
        # own line this turn (e.g. "Here's what I found on …", per the prompt's
        # step_2_visual) already introduces the cards — a second canned preamble
        # ("I've put together the key details…") was redundant, so it was removed.
        #
        # True overlap of generation and narration:
        #   • A background PRODUCER task drains the LLM stream continuously,
        #     pushing each card into a queue the instant its JSON object closes.
        #   • The foreground CONSUMER shows + narrates cards from the queue.
        # While card 1 is being narrated (~3-5 s), the producer keeps generating
        # cards 2,3,4 — so the next card is already waiting when narration ends,
        # with no gap between cards. First card still appears as soon as it's
        # generated (~1 s); the rest are effectively "free" behind the narration.
        card_queue: asyncio.Queue = asyncio.Queue()

        async def _produce_cards() -> None:
            try:
                async for payload in self.ui_agent_functions.query_process_stream(
                    user_input=user_input,
                    db_results=db_results,
                    agent_response=agent_response,
                    user_id=user_id,
                    media_map=getattr(self, "db_media_map", {}),
                ):
                    await card_queue.put(payload)
            except Exception as e:
                self.logger.warning("Card generation failed: %s", e)
            finally:
                await card_queue.put(None)  # sentinel: generation finished

        producer = asyncio.create_task(_produce_cards())

        all_cards: list[dict] = []
        while True:
            payload = await card_queue.get()
            if payload is None:  # producer done
                break
            if payload.get("type") == "error":
                continue

            narration = payload.pop("narration", "")
            card_index = len(all_cards)
            card_payload = {
                **payload,
                "stream_id":  f"{base_stream_id}-{card_index}",
                "card_index": card_index,
            }

            # Show this card immediately — don't wait for the rest of the batch.
            await self._publish_data_packet(card_payload, TOPIC_UI_FLASHCARD)
            self.logger.info("⚡ Card shown: %s", card_payload.get("title", ""))

            # Narrate it; the producer keeps generating later cards in the
            # background (event loop is free during this await).
            if narration and session:
                try:
                    await asyncio.wait_for(
                        session.say(narration, allow_interruptions=True),
                        timeout=12.0,
                    )
                    self.logger.debug("🔊 Narrated: %s", narration[:80])
                except asyncio.TimeoutError:
                    self.logger.warning("Narration timed out: %s", card_payload.get("title", ""))
                except Exception as e:
                    self.logger.warning("Narration failed: %s", e)

            all_cards.append(card_payload)

        await producer  # generation already finished; surface any leftover state

        # Fallback: if nothing was produced, ship one card built from the spoken
        # response so the agent's "I'm showing you the details" promise holds.
        if not all_cards and agent_response:
            fallback = {
                "type": "flashcard",
                "title": "Summary",
                "value": agent_response,
                "stream_id": f"{base_stream_id}-0",
                "card_index": 0,
                "fallback": True,
            }
            if await self._publish_data_packet(fallback, TOPIC_UI_FLASHCARD):
                all_cards.append(fallback)
                self.logger.info("⚠️ Published fallback flashcard from spoken response")

        if not all_cards:
            self.logger.warning("No cards generated — skipping publish")
            await self._publish_data_packet(
                {"type": "end_of_stream", "stream_id": f"{base_stream_id}-final", "card_count": 0},
                TOPIC_UI_FLASHCARD,
            )
            return

        # ── Browse mode — all cards in CardStack ─────────────────────────────
        final_stream_id = f"{base_stream_id}-final"
        for i, card_payload in enumerate(all_cards):
            republish = {**card_payload, "stream_id": final_stream_id, "card_index": i}
            await self._publish_data_packet(republish, TOPIC_UI_FLASHCARD)

        await self._publish_data_packet(
            {"type": "end_of_stream", "stream_id": final_stream_id, "card_count": len(all_cards)},
            TOPIC_UI_FLASHCARD,
        )
        self.logger.info(
            "✅ Browse mode: %d card(s) published (stream=%s)", len(all_cards), final_stream_id
        )

        # ── Combined "explain THEN navigate" — only when the user asked for both ──
        # The cards have finished explaining; now open the page and announce it.
        # The redirect line is the CLOSER — no follow-up question after it.
        navigated = False
        if navigate_to:
            res = await self._resolve_navigation(navigate_to)
            if res and res["status"] in ("high", "medium"):
                await self._do_navigate(res["url"], res["path"], res["title"])
                navigated = True
                if session:
                    try:
                        await asyncio.wait_for(
                            session.say(
                                f"And I've redirected you to the {res['title']} page.",
                                allow_interruptions=True,
                            ),
                            timeout=10.0,
                        )
                    except Exception as e:
                        self.logger.debug("Redirect line skipped: %s", e)
            else:
                self.logger.info("navigate_to %r did not resolve confidently — skipping nav", navigate_to)

        # Follow-up question restarts the silence watchdog (it was cleared by the
        # non-question narrations; the "?" here re-arms it). Skipped when we
        # navigated — the redirect line is the closer (no follow-up).
        if not navigated and session:
            try:
                await session.say(
                    "Is there anything specific you'd like to know more about?",
                    allow_interruptions=True,
                )
            except Exception as e:
                self.logger.debug("Follow-up question skipped: %s", e)
