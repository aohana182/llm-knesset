# LLM Knesset

A multi-model AI council that runs queries through a 3-stage deliberation process: parallel responses, peer ranking, and chairman synthesis.

## Architecture

- **Backend**: Python / FastAPI (`backend/`), served via uvicorn on port 8000
- **Frontend**: React + Vite (`frontend/`), dev server on port 5000; production build served by the FastAPI static file handler
- **Database**: Replit PostgreSQL (persistent across deployments)

## Workflows

- `Backend API` — starts uvicorn (`python main.py`)
- `Start application` — runs `npm run dev` in `frontend/`

## Backend Structure

| File | Purpose |
|---|---|
| `backend/main.py` | FastAPI app, all API endpoints |
| `backend/council.py` | 3-stage LLM orchestration (stage1, stage2, stage3) |
| `backend/openrouter.py` | OpenRouter API calls (parallel + single) |
| `backend/db.py` | PostgreSQL connection pool (psycopg2) |
| `backend/storage.py` | Conversation CRUD — PostgreSQL-backed |
| `backend/settings_store.py` | Global settings (API key, models, admin emails) — PostgreSQL-backed |
| `backend/user_store.py` | Per-user model preferences — PostgreSQL-backed |
| `backend/auth.py` | Firebase token verification + JWT session cookies |
| `backend/config.py` | Config constants and getter functions |

## Database Schema

- `settings` — key/value pairs (API key, model lists, admin emails)
- `conversations` — id, user_id, created_at, title
- `messages` — conversation_id, role, content (JSONB with full stage1/stage2/stage3 data)
- `user_prefs` — user_id, prefs (JSONB)

## Key Design Decisions

- Conversations are scoped to users via Firebase auth (`user_id` = Firebase UID)
- Each conversation is currently single-turn (one query → full council deliberation)
- The chairman synthesizes rather than simply picking the top-ranked response
- Title generation always uses `google/gemini-2.5-flash` regardless of council settings
- SSE streaming delivers stage events progressively to the frontend
