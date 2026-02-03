# Indusnet AI Website Backend

A LiveKit-powered AI voice agent backend for Indus Net Technologies website, providing intelligent conversational experiences with dynamic UI flashcard generation.

## Features

- **Voice AI Agent**: Real-time voice interaction using LiveKit Agents with GPT-4 Realtime
- **Dynamic UI Generation**: Generates visual flashcards synchronized with voice responses
- **Knowledge Base Search**: Vector database powered by ChromaDB with Indus Net company information
- **Multi-language Support**: English, Hindi, and Bengali with natural code-mixing
- **Background Audio**: Ambient office sounds and typing effects during processing

## Architecture

```
src/
├── agents/              # AI Agent logic
│   ├── indusnet/       # Indusnet-specific agent implementation
│   ├── base.py         # Base agent class
│   ├── factory.py      # Agent factory pattern
│   └── session.py      # LiveKit session management
├── api/                # FastAPI REST endpoints
│   ├── routes/         # API route handlers
│   └── models/         # Pydantic schemas
├── core/               # Core configuration
│   ├── config.py       # Environment settings
│   └── logger.py       # Logging setup
└── services/           # External service integrations
    ├── livekit/        # LiveKit room & token management
    ├── openai/         # OpenAI integration for UI generation
    └── vectordb/       # ChromaDB vector knowledge base
```

## Prerequisites

- Python 3.12+
- UV package manager (recommended) or pip
- LiveKit server (self-hosted or cloud)
- OpenAI API key
- Cartesia API key

## Environment Variables

Create a `.env` file in the project root:

```env
# LiveKit Configuration
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-livekit-server.com

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Cartesia TTS Configuration
CARTESIA_API_KEY=your_cartesia_api_key

# Server Configuration
PORT=8000
```

## Installation

### Using UV (Recommended)

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows
```

### Using pip

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .
```

## Running the Application

### 1. Start the API Server

```bash
# Development mode
python -m src.api.main

# Production mode (with Gunicorn)
python server_run.py
```

The API server will start on `http://localhost:8000`

### 2. Start the LiveKit Agent

```bash
# Development mode with auto-reload
python -m livekit.agents.cli dev

# Production mode
python -m livekit.agents.cli start
```

## API Endpoints

### Health Check
```
GET /health
```

### Generate Room Token
```
GET /api/getToken?name=guest&agent=indusnet&room=optional-room-name
```

**Query Parameters:**
- `name`: User identity (default: "guest")
- `agent`: Agent type (must be "indusnet")
- `room`: Optional room name (auto-generated if not provided)

**Response:** JWT token for LiveKit room access

## Agent Features

### Voice Interaction
- Real-time conversation with GPT-4 Realtime model
- Sonic-3 TTS by Cartesia for natural voice output
- Automatic transcription and humanized responses
- Noise cancellation support

### UI Synchronization
- Generates flashcards based on conversation context
- Prevents duplicate content with deduplication logic
- Supports multiple visual intents (neutral, urgent, success, cyberpunk)
- Dynamic media from Pixabay/Pexels or curated assets

### Knowledge Base
- Pre-loaded Indus Net Technologies information
- Vector similarity search using ChromaDB
- Text embeddings via OpenAI `text-embedding-3-small`
- Excel data source: `src/services/vectordb/chroma_db/website_extracted_data.xlsx`

## Project Structure Details

### Agent Types
- **IndusnetAgent**: Main agent for Indus Net website interactions
  - Knowledge base search tool
  - UI flashcard publishing tool
  - Multi-language support (English, Hindi, Bengali)

### UI Flashcard Schema
Cards are generated with the following properties:
- `title`: Card heading
- `value`: Main content (supports markdown)
- `visual_intent`: Color theme (neutral, urgent, success, etc.)
- `animation_style`: Entry animation (slide, pop, fade, flip, scale)
- `icon`: Lucide icon reference
- `media`: Images/videos from stock sources or curated assets
- `layout`: Card layout type (default, horizontal, centered, media-top)
- `size`: Card size (sm, md, lg)

## Development

### File Naming Conventions
- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/Variables: `snake_case`
- Services: `*_svc.py` suffix

### Key Files
- `src/agents/indusnet/agent.py`: Main agent logic
- `src/agents/indusnet/prompts.py`: Voice agent system prompt
- `src/services/openai/indusnet/ui_system_prompt.py`: UI generation prompt
- `src/services/openai/indusnet/openai_scv.py`: OpenAI streaming service
- `src/agents/session.py`: LiveKit session entry point

## Deployment

### Docker
See `docker-compose.yml` for containerized deployment.

### Production Considerations
- Use `server_run.py` with Gunicorn for production API server
- Configure proper CORS origins in `src/api/main.py`
- Set up reverse proxy (Nginx/Caddy) for HTTPS
- Monitor LiveKit agent process with systemd or supervisor
- Implement rate limiting for token generation endpoint

## Troubleshooting

### Import Errors
- Ensure virtual environment is activated
- Run `uv sync` or `pip install -e .` to install dependencies

### LiveKit Connection Issues
- Verify `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`
- Check LiveKit server status
- Ensure firewall allows WebSocket connections

### Agent Not Responding
- Check OpenAI API key is valid
- Verify Cartesia API key for TTS
- Review logs in `src/core/logger.py` output

## License

Proprietary - Indus Net Technologies

## Support

For issues or questions, contact the Indus Net Technologies development team.
