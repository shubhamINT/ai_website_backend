# Implementation Plan: Dual-Layer Memory System

This plan implements a production-grade memory system with two complementary layers:
1. **Session History** (Zep-style): Complete replay of UI states and conversations within a session
2. **User Persona** (Mem0): Cross-session fact extraction and personalization

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     AI Agent                            │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────────┐      ┌─────────────────────┐    │
│  │ Session History  │      │  User Persona (Mem0)│    │
│  │  (Per Session)   │      │ (Cross-Session)     │    │
│  ├──────────────────┤      ├─────────────────────┤    │
│  │ • Messages       │      │ • Facts/Preferences │    │
│  │ • UI Cards Shown │      │ • Interests         │    │
│  │ • Timestamps     │      │ • Professional Info │    │
│  │ • Voice Nav      │      │ • Vector Search     │    │
│  └──────────────────┘      └─────────────────────┘    │
│           │                          │                 │
│           └──────────┬───────────────┘                 │
│                      ▼                                 │
│           PostgreSQL + pgvector                        │
└─────────────────────────────────────────────────────────┘
```

## Do We Need a Vector DB?

**Answer: Use pgvector extension in PostgreSQL**
- Mem0 requires vector storage for semantic fact retrieval → **pgvector**
- ChromaDB already handles knowledge base search → **keep separate**
- Session history can use standard SQL → **Postgres tables**
- **No need for a separate vector DB** (Redis Vector, Qdrant, etc.)

## Proposed Changes

### Database Layer
#### [MODIFY] [docker-compose.yml](file:///home/shubhan_halder/CODE/LIVEKIT/ai_website_backend/docker-compose.yml)
- Add PostgreSQL service with `pgvector` extension enabled
- Configure volume for data persistence
- Add health checks

#### [MODIFY] [config.py](file:///home/shubhan_halder/CODE/LIVEKIT/ai_website_backend/src/core/config.py)
- Add `DATABASE_URL` and Postgres credentials

### Memory Implementation
#### [NEW] [memory_svc.py](file:///home/shubhan_halder/CODE/LIVEKIT/ai_website_backend/src/services/memory/memory_svc.py)
Create `DualLayerMemory` with:

**Layer 1: SessionHistory**
- Table schema: `session_messages(id, session_id, role, content, ui_cards_json, timestamp)`
- Methods:
  - `append(session_id, role, content, ui_cards)` - Record each turn
  - `get_session_history(session_id, last_n)` - Retrieve recent messages
  - `get_ui_card_at_turn(session_id, turn_index)` - Voice navigation

**Layer 2: UserPersona (Mem0)**
- Configure Mem0 with Postgres + pgvector backend
- Extract facts from conversations automatically
- Methods:
  - `extract_facts(user_id, message)` - Called after each user message
  - `get_user_profile(user_id)` - Retrieve stored persona
  - `search_memories(user_id, query)` - Semantic search

### Agent Integration
#### [MODIFY] [agent.py](file:///home/shubhan_halder/CODE/LIVEKIT/ai_website_backend/src/agents/indusnet/agent.py)
- Initialize `DualLayerMemory` in `__init__`
- On each user message:
  1. Store in session history with UI cards shown
  2. Extract facts for persona (async)
- On session start:
  1. Load user persona from Mem0
  2. Inject into system prompt ("You previously learned this user is...")
- Add voice command handler:
  - "Show me the second card again" → `get_ui_card_at_turn(session_id, 2)`
  - "What did we talk about 3 questions ago?" → `get_session_history(session_id, offset=3)`

#### [NEW] Voice Commands Function Tool
```python
@function_tool
async def navigate_history(context, instruction: str):
    """Navigate through conversation history by voice.
    Examples: 'show the 2nd card', 'what did we discuss earlier', 'go back 3 steps'
    """
```

### API Layer
#### [NEW] [history.py](file:///home/shubhan_halder/CODE/LIVEKIT/ai_website_backend/src/api/routes/history.py)
- `GET /api/history/{session_id}` - Full session replay
- `GET /api/persona/{user_id}` - User profile summary

## Verification Plan

### Automated Tests
- Simulate 5-turn conversation and verify all UI cards are stored
- Extract session history at turn 3 and validate card data
- Test Mem0 fact extraction with sample phrases

### Manual Verification
1. **Session Replay**: Have a 3-turn conversation with UI cards. Say "show me the first card again" via voice.
2. **Persona Building**: Tell the agent "I'm a React developer interested in cloud migration." End session. New session: ask "What do you know about me?"
3. **History API**: Call `/api/history/{session_id}` and verify all cards are reconstructable.
