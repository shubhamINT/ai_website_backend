"""
UI Agent for generating flashcard content using OpenAI and Mem0.
"""

import asyncio
import json
import logging
import re
from typing import Any, AsyncGenerator, Optional

import os
from mem0 import Memory
from openai import AsyncOpenAI

from src.core.config import settings
from src.services.llm.infographic import (
    normalize_infographic_payload,
    normalize_sections,
    normalize_chips,
)
from src.services.llm.prompts import UI_SYSTEM_INSTRUCTION, VAANI_UI_SYSTEM_INSTRUCTION
from src.services.llm.media_assets import (
    MEDIA_ASSETS,
    local_asset_url,
    library_image_url,
    list_library_images,
)

# ── Backend keyword → curated asset fallback ──────────────────────────────────
# When the LLM omits an asset_key for a card whose topic clearly maps to a curated
# image/video, we infer it here. More specific patterns come first (Kolkata before
# generic "office"). All keyword checks are lower-case substring matches.
_KEYWORD_ASSET_MAP: list[tuple[tuple[str, ...], str]] = [
    # Offices (specific before generic)
    (('kolkata', 'saltlake', 'newtown', 'ecospace', 'headquarters', 'hq office'), 'kolkata_office'),
    (('office', 'workplace', 'workspace', 'building', 'facility', 'campus', 'premises',
      'environment', 'office environment', 'office space'), 'indus_office'),
    # Leadership
    (('abhishek', 'rungta', 'founder & ceo', 'founder and ceo'), 'ceo_abhishek_rungta'),
    (('ceo', 'chief executive'), 'ceo_video'),
    # Company/intro
    (('about us', 'who we are', 'our story', 'company overview', 'introduction'), 'intro_video'),
    # Global presence
    (('global presence', 'worldwide', 'international office', 'our locations', 'global map'), 'global_map'),
    # Careers
    (('career', 'hiring', 'recruitment', 'join us', 'work with us', 'life at int'), 'careers_video'),
    # Contact
    (('contact', 'reach out', 'get in touch', 'reach us'), 'contact'),
    # Services
    (('cybersecurity', 'cyber security', 'vapt', 'penetration test', 'soc ', 'security operations'), 'cybersecurity'),
    (('cloud', 'devops', 'kubernetes', 'docker', 'infrastructure'), 'cloud_devops'),
    (('artificial intelligence', 'machine learning', ' ai ', 'analytics', 'data science'), 'ai_analytics'),
    (('digital engineering', 'software development', 'product engineering'), 'digital_engineering'),
    (('customer experience', ' cx ', 'ux design', 'user experience'), 'customer_experience'),
    # Case studies
    (('sbig', 'sbi general'), 'case_sbig'),
    (('cashpoint',), 'case_cashpoint'),
    (('dcb bank', 'dcb'), 'case_dcb_bank'),
    # Partners
    (('microsoft', ' azure'), 'partner_microsoft'),
    ((' aws ', 'amazon web'), 'partner_aws'),
    (('google cloud', ' gcp '), 'partner_google'),
    # Testimonials
    (('malcolm',), 'testimonial_malcolm'),
    (('michael',), 'testimonial_michael'),
    (('tapan',), 'testimonial_tapan'),
    (('aniket',), 'testimonial_aniket'),
]


def _infer_asset_key(text: str) -> str:
    """Keyword fallback: return a curated asset_key if `text` matches a known
    topic, or '' if nothing matches."""
    t = f" {text.lower()} "  # pad with spaces so word-boundary checks work
    for keywords, asset_key in _KEYWORD_ASSET_MAP:
        if any(kw in t for kw in keywords):
            return asset_key
    return ""


class UIAgentFunctions:
    def __init__(self, mode: str = 'vaani'):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.llm_model = settings.FLASHCARD_MODEL
        self.logger = logging.getLogger(__name__)
        self._base_instructions = VAANI_UI_SYSTEM_INSTRUCTION if mode == 'vaani' else UI_SYSTEM_INSTRUCTION
        self.instructions = self._base_instructions

        mem0_config = {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4o-mini",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                },
            },
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": "ui_flashcard_memory",
                    "path": f"{settings.BASE_DIR}/src/services/vectordb/chroma_db_mem0",
                },
            },
        }
        self.memory = Memory.from_config(mem0_config)
        self.logger.info("Mem0 memory initialized with ChromaDB backend")

    async def query_process_stream(
        self,
        user_input: str,
        db_results: str,
        agent_response: str | None = None,
        user_id: str | None = None,
        media_map: dict | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Generate flashcard payloads for the given user input and DB results.
        Automatically saves the full batch to Mem0 after streaming completes.
        """
        import asyncio

        try:
            self.logger.info("Starting UI stream generation ...")

            effective_agent_response = (
                agent_response or "Analyze DB Results to predict the response."
            )

            # Live catalog of local library images. The model picks one BY NAME
            # per card (media.local_image) — preferred over any external URL.
            # Rebuilt every call, so newly-added images/folders appear instantly.
            library_images = list_library_images()
            if library_images:
                listing = "\n".join(f"  - {p}" for p in library_images)
                library_block = (
                    "\n\n## VAANI Library Images (LOCAL — use these first)\n"
                    "These real images live in our library. For each card, if one of them\n"
                    "fits the card's topic, set media.local_image to its EXACT path below\n"
                    "(copy it verbatim). Prefer these over any external/curated image. Pick\n"
                    "the image whose NAME best matches the card. If none fit, omit local_image.\n"
                    f"{listing}\n"
                )
            else:
                library_block = ""

            prompt_content = f"""
                ## User's Question
                {user_input}

                ## Agent's Spoken Response
                {effective_agent_response}

                ## Database Results (Raw Reference)
                {db_results}
                {library_block}
                ## Your Task
                Generate as many cards as the answer genuinely needs (typically 1 to 6) for NEW information only. Each card is either an image "flashcard" or a composed text "infographic" (hero + typed blocks) — mix the two only when it genuinely helps. Check active_elements and skip any content already displayed.
            """

            stream = await self.openai_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": self.instructions},
                    {"role": "user", "content": prompt_content},
                ],
                response_format={"type": "json_object"},
                stream=True,
                temperature=0.5,
                timeout=20.0,  # don't hang the card stream on a stalled API call
            )

            generated_cards: list[dict] = []
            media_map = media_map or {}
            used_media: set[str] = set()  # dedup images across this card batch

            async with stream:
                buffer = ""
                state = 0

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        buffer += chunk.choices[0].delta.content

                        if state == 0:
                            match = re.search(r'"cards"\s*:\s*\[', buffer)
                            if match:
                                buffer = buffer[match.end() :]
                                state = 1

                        if state == 1:
                            while True:
                                start_idx = buffer.find("{")
                                if start_idx == -1:
                                    break

                                # ponytail: brace depth must ignore { } inside string literals
                                depth = 0
                                end_idx = -1
                                in_str = False
                                esc = False

                                for k in range(start_idx, len(buffer)):
                                    c = buffer[k]
                                    if in_str:
                                        if esc:
                                            esc = False
                                        elif c == "\\":
                                            esc = True
                                        elif c == '"':
                                            in_str = False
                                        continue
                                    if c == '"':
                                        in_str = True
                                    elif c == "{":
                                        depth += 1
                                    elif c == "}":
                                        depth -= 1
                                        if depth == 0:
                                            end_idx = k
                                            break

                                if end_idx != -1:
                                    raw_json = buffer[start_idx : end_idx + 1]

                                    try:
                                        card_obj = json.loads(raw_json)
                                        payload = await self._normalize_card_payload(
                                            card_obj, media_map, used_media,
                                        )
                                        if payload:
                                            generated_cards.append(payload)
                                            yield payload
                                    except Exception:
                                        pass

                                    buffer = buffer[end_idx + 1 :]
                                else:
                                    break

            asyncio.create_task(
                self._save_to_memory(
                    user_query=user_input,
                    cards=generated_cards,
                    user_id=user_id,
                )
            )

        except Exception as e:
            yield {"type": "error", "content": str(e)}

    async def recall_ui_content(
        self, agent_response: str, user_id: str
    ) -> Optional[list[dict]]:
        """Search Mem0 for previously shown flashcard batch."""
        import asyncio

        if not user_id:
            self.logger.warning("recall_ui_content called with no user_id")
            return None

        self.logger.info(
            "Recalling UI content from Mem0 for: '%s' (user: %s)",
            agent_response,
            user_id,
        )

        try:
            results = await asyncio.to_thread(
                self.memory.search, query=agent_response, user_id=user_id, limit=1
            )

            if not results or not results.get("results"):
                self.logger.info("No Mem0 results found for: %s", agent_response)
                return None

            top_result = results["results"][0]
            metadata = top_result.get("metadata", {})

            if "cards" in metadata:
                try:
                    cards = json.loads(metadata["cards"])
                    self.logger.info(
                        "Recalled %d flashcard(s) from Mem0 metadata for user %s",
                        len(cards),
                        user_id,
                    )
                    return cards
                except Exception as e:
                    self.logger.error("Failed to parse cards from Mem0 metadata: %s", e)

            memory_text: str = top_result.get("memory", "")
            if not memory_text:
                return None

            if "| cards: " in memory_text:
                cards_json_str = memory_text.split("| cards: ", 1)[1]
                cards = json.loads(cards_json_str)
                self.logger.info(
                    "Recalled %d flashcard(s) from legacy Mem0 text for user %s",
                    len(cards),
                    user_id,
                )
                return cards

            return None

        except Exception as e:
            self.logger.error("Mem0 recall failed: %s", e)
            return None

    async def _save_to_memory(
        self,
        user_query: str,
        cards: list[dict],
        user_id: str | None,
    ) -> None:
        """Persist the flashcard batch to Mem0 for later recall."""
        import asyncio

        if not user_id:
            self.logger.info("Skipping Mem0 save — no user_id (guest session)")
            return

        if not cards:
            self.logger.info("Skipping Mem0 save — no cards generated")
            return

        try:
            cards_json = json.dumps(cards)
            memory_content = (
                f"The user viewed flashcards for the query: '{user_query}'."
            )

            await asyncio.to_thread(
                self.memory.add,
                messages=[{"role": "user", "content": memory_content}],
                user_id=user_id,
                metadata={
                    "topic": "ui_flashcard",
                    "user_query": user_query,
                    "cards": cards_json,
                },
            )

            self.logger.info(
                "Saved %d flashcard(s) to Mem0 metadata for user %s (query: '%s')",
                len(cards),
                user_id,
                user_query,
            )
        except Exception as e:
            self.logger.error("Mem0 save failed: %s", e)

    def _resolve_media(
        self,
        media_data: dict,
        media_map: dict,
        used_media: set,
        card_title: str,
    ) -> dict:
        """Resolve a card's media. Priority:
          1. asset_key      → curated INT asset (CEO / office / VIDEO / case-study
                               library — kept; we don't rely on the scrape for these).
          2. source_result  → the scraped block this card is based on (by index);
                               we attach THAT block's real image. No id-copying.
          3. poster_label   → styled text poster (ALWAYS available as fallback).
        No web image search. An image used once is not reused on a later card
        (dedup) — the duplicate falls back to a poster instead.
        Every card returns a non-empty media block so card size stays uniform."""

        def try_asset(key: str) -> dict | None:
            """Return media dict if `key` is a valid, unused curated asset.

            Local-first: a matching image in the VAANI Library asset folder wins
            over the external URL (see media_assets.local_asset_url)."""
            if not key or key not in MEDIA_ASSETS:
                return None
            local = local_asset_url(key)
            urls = [local] if local else MEDIA_ASSETS[key].get("urls", [])
            if not urls:
                return None
            if urls[0] in used_media:
                return None  # duplicate in this batch
            for u in urls:
                used_media.add(u)
            return {"urls": urls}

        # 0) Library image the LLM picked BY NAME — highest priority, fully local.
        #    Falls through to the curated/scraped paths below if it doesn't resolve.
        chosen = (media_data.get("local_image") or media_data.get("library_image") or "").strip()
        if chosen:
            lib_url = library_image_url(chosen, used_media)
            if lib_url:
                used_media.add(lib_url)
                return {
                    "urls": [lib_url],
                    "poster_label": (media_data.get("poster_label") or card_title or "").strip(),
                }

        # 1a) Explicit curated asset_key from the LLM
        explicit = (media_data.get("asset_key") or "").strip()
        if result := try_asset(explicit):
            return result

        # Identify source block by index (LLM outputs source_result: N)
        sr = media_data.get("source_result")
        try:
            sr = int(sr)
        except (TypeError, ValueError):
            sr = None
        block = media_map.get(sr, {}) if sr is not None else {}

        media_id = block.get("media_id") or (media_data.get("media_id") or "").strip()
        poster_label = (
            (media_data.get("poster_label") or "").strip()
            or block.get("poster_label", "")
            or block.get("title", "")
        )

        # 1b) Backend keyword inference — catches missed asset_key bindings.
        # Run BEFORE the scraped image so curated > scraped, but only when the
        # LLM gave no (or wrong) explicit key.
        search_text = f"{card_title} {poster_label} {block.get('title', '')}"
        if inferred := _infer_asset_key(search_text):
            if result := try_asset(inferred):
                return result

        # 2) Scraped block image — deduplicated by actual URL
        if media_id:
            webp = os.path.join(settings.MEDIA_DIR, f"{media_id}.webp")
            if os.path.isfile(webp):
                img_url = f"{settings.MEDIA_BASE_URL}/media/{media_id}.webp"
                if img_url not in used_media:
                    used_media.add(img_url)
                    return {
                        "urls": [img_url],
                        "poster_label": poster_label or card_title,
                    }
                # duplicate scraped image → fall through to poster

        # 3) No image found — text poster.
        # Use "no_image" sentinel so the frontend can show a "visual unavailable"
        # state instead of a misleading topic label when the user explicitly asked
        # for pictures/images.
        label = (poster_label or card_title or "INT.").strip()
        return {"poster_label": label}

    async def _normalize_card_payload(
        self,
        card_obj: dict,
        media_map: dict | None = None,
        used_media: set | None = None,
    ) -> dict | None:
        if not isinstance(card_obj, dict):
            return None

        # A deck card is either an image "flashcard" or a composed text "infographic".
        card_type = card_obj.get("type") or "flashcard"

        if card_type in ("infographic", "rich_card"):
            # "rich_card" is the legacy alias (kept so old Mem0-recalled cards still
            # render) — normalize it to an infographic so the frontend only ever
            # handles two card types: image "flashcard" and text "infographic".
            return normalize_infographic_payload(card_obj)

        payload: dict[str, Any] = {"type": "flashcard"}

        for key in ("id", "title", "value", "items", "tagline", "visual_intent", "icon", "narration"):
            if key in card_obj and card_obj[key] is not None:
                payload[key] = card_obj[key]

        if "title" not in payload:
            return None

        # Always resolve media → every card gets an image OR a text poster, so
        # cards never collapse to a smaller, imageless size. _resolve_media is
        # library-first (local VAANI Library photos win over external links).
        media_data = card_obj["media"] if isinstance(card_obj.get("media"), dict) else {}
        payload["media"] = self._resolve_media(
            media_data,
            media_map or {},
            used_media if used_media is not None else set(),
            str(payload.get("title", "")),
        )

        if "visual_intent" not in payload and "intent" in card_obj:
            payload["visual_intent"] = card_obj["intent"]

        # Rich layer: a flashcard may carry the same typed blocks an infographic
        # uses (stats/icon_bullets/cta_banner/...) alongside its image. Validated
        # by the shared infographic helpers; absent → renders as before (image + value).
        sections = normalize_sections(card_obj.get("sections"))
        if sections:
            payload["sections"] = sections
        chips = normalize_chips(card_obj.get("chips"))
        if chips:
            payload["chips"] = chips

        payload.setdefault("value", "")  # rich image+sections card may omit value; keep it

        return payload

    async def update_instructions_with_context(self, ui_context: dict) -> None:
        self.logger.info("Updating instructions with UI context")
        md = []
        for key, value in ui_context.items():
            md.append(
                f"**{key}**: `{json.dumps(value, indent=2, default=str) if isinstance(value, (dict, list)) else value}`"
            )

        self.instructions = (
            self._base_instructions
            + "\n\nThe following is the current UI state. Generate the visual accordingly:\n\n"
            + "\n".join(md)
        )
