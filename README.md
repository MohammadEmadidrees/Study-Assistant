# Study Assistant AI — Production Chatbot Web Application

A production-structured AI study assistant web application built with **FastAPI**, **Next.js (App Router)**, **PostgreSQL**, **Redis**, and the **Anthropic Claude API** (via an extensible LLM adapter pattern). Supports real-time Server-Sent Events (SSE) streaming, dual-tier memory management, rate limiting, and structured logging.

---

## Architecture Overview

```
Study Assistant/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── health.py        # GET /api/v1/health
│   │   │       │   ├── chat.py          # POST /api/v1/chat & POST /api/v1/chat/stream
│   │   │       │   └── sessions.py      # Session history CRUD
│   │   │       └── router.py
│   │   ├── core/
│   │   │   ├── config.py                # pydantic-settings validated environment variables
│   │   │   ├── database.py              # Async SQLAlchemy engine & resilient connection pool
│   │   │   ├── redis.py                 # Async Redis manager with fallback
│   │   │   ├── logging.py               # Structured JSON logging (X-Request-ID, latency, tokens)
│   │   │   └── rate_limiter.py          # Sliding window rate limiter (session & IP)
│   │   ├── models/                      # SQLAlchemy models: User, Conversation, Message
│   │   ├── schemas/                     # Pydantic v2 schemas: Chat, Session, StreamChunk
│   │   ├── services/
│   │   │   ├── llm_provider.py          # Abstract Base Class + ClaudeProvider adapter
│   │   │   ├── orchestrator.py          # Prompt assembly, role alternation, token metrics
│   │   │   └── memory.py                # Dual-layer storage (Postgres archive + Redis cache)
│   │   └── main.py                      # FastAPI app, lifespan, CORS, and error handlers
│   ├── alembic/                         # Database schema migrations
│   ├── tests/                           # Pytest test suite (13 automated tests)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/                         # Next.js 14 App Router (layout.tsx, page.tsx)
│   │   ├── components/                  # Sidebar, MessageItem, ChatInput, Header
│   │   ├── hooks/useChatStream.ts       # SSE streaming reader with stop control
│   │   ├── lib/api.ts                   # REST client for sessions and health
│   │   └── types/chat.ts                # TypeScript definitions
│   └── package.json
└── docker-compose.yml                   # PostgreSQL 15 & Redis 7 services
```

---

## Key Features

1. **Adapter Pattern for LLMs (`services/llm_provider.py`)**:
   - `BaseLLMProvider` abstract base class defining `generate()` and `stream()`.
   - `ClaudeProvider` adapter wrapping the Anthropic Python SDK.
   - Adding a new provider requires implementing `BaseLLMProvider` in `llm_provider.py` without touching route handlers.

2. **Dual-Tier Conversation Memory (`services/memory.py`)**:
   - **PostgreSQL**: Authoritative relational persistence of all historical transcripts.
   - **Redis**: Low-latency cache of the active session's recent $N$ messages for fast prompt assembly.
   - **Resilience**: Auto-hydrates Redis on cache miss and gracefully degrades to SQLite/memory if external databases are temporarily unavailable.

3. **Server-Sent Events (SSE) Streaming (`POST /api/v1/chat/stream`)**:
   - Emits typed JSON chunks (`{"session_id": "...", "delta": "...", "done": false}`).
   - Detects client disconnections to cancel long-running model generations.
   - Stop generation button in UI via client-side `AbortController`.

4. **Production Hardening**:
   - **Rate Limiting**: Sliding window rate limiter (20 requests/minute per session/IP).
   - **Structured Logging**: Contextual JSON logs with `X-Request-ID`, `latency_ms`, and token usage (no message content at INFO level).
   - **Graceful Error Handling**: Custom global exception handlers translate LLM timeouts and quota errors to user-facing 502 messages instead of raw 500 crashes.

---

## Quickstart Guide

### 1. Database & Cache Services (Docker)
```bash
docker compose up -d
```

### 2. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # or .\.venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env

# Run database migrations
alembic upgrade head

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to open the application.

---

## Automated Test Suite

Run the full pytest suite from the `backend/` directory:
```bash
pytest -v
```

All 13 unit and integration tests verify:
- Health check & database connection
- Single-turn chat and prompt assembly
- SSE token-by-token streaming
- Dual-tier memory persistence & session CRUD
- Rate limiting triggers & graceful LLM error handling
- Multi-turn conversation continuity
