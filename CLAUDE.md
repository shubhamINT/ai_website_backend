# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install deps
uv sync
source .venv/bin/activate

# Run API server (dev)
python -m src.api.main

# Run agent worker (dev)
python -m src.agents.session dev

# Run both together
bash run_both.sh

# Docker
docker compose up --build

# Create admin user
python scripts/create_admin.py

# Build MkDocs site (served at /documentation)
mkdocs build
```

No test suite exists. No linter config beyond ruff cache.

## Architecture

Two processes run independently and must both be up for the system to work:

1. **FastAPI** (`src/api/main.py`) — HTTP API for auth and LiveKit token issuance. Connects to MongoDB on startup via `init_db()`.
2. **Agent Worker** (`src/agents/session.py`) — LiveKit Agents worker. Dispatched per room. Runs `IndusNetAgent` for each voice conversation.

### Request → Conversation Flow

1. Frontend calls `GET /api/getToken` → FastAPI creates a LiveKit room, dispatches the `indusnet` agent, returns JWT.
2. Frontend joins room with JWT.
3. LiveKit dispatches a job to the agent worker → `entrypoint()` in `session.py` runs.
4. `AgentSession` uses OpenAI Realtime (LLM + transcription) + Cartesia TTS (sonic-3).
5. `IndusNetAgent` handles conversation, calls tool functions, publishes data packets to frontend via LiveKit data channels.

### IndusNetAgent Composition

`IndusNetAgent` in `src/agents/indusnet/agent.py` is assembled entirely through multiple inheritance (MRO order matters):

```
AgentState → PacketHelperMixin → VectorSearchHelperMixin → DataHandlerMixin
→ [Tool Mixins: Knowledge, UIPublisher, Forms, Location, Meeting, Email, WhatsApp, User, EndCall]
→ BaseAgent
```

All tool functions decorated with `@function_tool` are auto-registered by LiveKit from the mixin classes. Never put tool logic directly in `IndusNetAgent` — add a mixin in `tools/`.

### Data Packet Bus

Agent ↔ frontend communicate via LiveKit room data packets (not HTTP). Two directions:

- **Frontend → Agent** (listened via `ctx.room.on("data_received")`): topics `user.context`, `user.location`, `ui.context`
- **Agent → Frontend** (published via `PacketHelperMixin`): topics `ui.flashcard`, `ui.contact_form`, `ui.job_application`, `ui.meeting_form`, `ui.location_request`, `ui.global_presense`, `ui.nearby_offices`, `ui.email_delivery`, `ui.whatsapp_delivery`, `user.details`

See `docs/architecture.md` for the full packet contract table.

### Services

| Service | Location | Purpose |
|---|---|---|
| VectorStoreService | `src/services/vectordb/vectordb_svc.py` | ChromaDB similarity search over `company_knowledge` collection; persisted at `src/services/vectordb/chroma_db/` |
| UIAgentFunctions | `src/services/llm/ui_agent.py` | GPT-4o-mini calls for flashcard generation |
| SearXNGService | `src/services/search/searxng_svc.py` | Web + image search via self-hosted SearXNG |
| GoogleMapService | `src/services/map/googlemap/services.py` | Distance/route calculation |
| LiveKitService | `src/services/livekit/livekit_svc.py` | Room creation, agent dispatch, JWT issuance |

### Auth System

JWT-based, stored in `auth_session` cookie (JSON string `{"token": "..."}`). Two flows:
- Email/password → `POST /auth/login`
- Google OAuth → `GET /auth/google` → Google → `GET /auth/google/callback` → redirect to Next.js

Roles: `admin` (30-day JWT, `@ADMIN_DOMAIN` Google accounts) and `client` (4h JWT, access window from first login).

FastAPI deps: `get_current_user` and `require_admin` in `src/auth/dependencies.py`.

No user registration endpoint — use `scripts/create_admin.py` or insert directly into MongoDB. See `docs/auth.md` for schema and manual insert examples.

### Config

All config in `src/core/config.py` via `settings` singleton. All values read from `.env` via `python-dotenv`. Key groups:
- LiveKit: `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `LIVEKIT_URL`
- OpenAI: `OPENAI_API_KEY`
- Cartesia: `CARTESIA_API_KEY`
- MongoDB: `MONGODB_URL`, `MONGODB_DB_NAME`
- Auth: `SECRET_KEY`, `ADMIN_DOMAIN`, `CLIENT_SESSION_HOURS`, `CLIENT_ACCESS_WINDOW_HOURS`
- Google OAuth: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `NEXTJS_CALLBACK_URL`
- Optional: `SMTP_*`, `WHATSAPP_*`, `SEARXNG_BASE_URL`, `GOOGLE_API_KEY`

### Logging

`src/core/logger.py` — rotating file handler writing to `logs/app.log`. Call `setup_logging()` once at process startup (done in both `main.py` and `session.py`).

## Key Caveats

- CORS is open (`*`) — tighten before production.
- ChromaDB is file-persisted locally; not suitable for multi-instance deployments without changes.
- `run_both.sh` has a dependency preflight that auto-runs `uv sync --frozen` if imports fail.
- MkDocs static site (`mkdocs build`) is served at `/documentation` if the `site/` dir exists.
- `SECRET_KEY` must be set; generate with `openssl rand -hex 32`.
