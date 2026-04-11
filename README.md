# llm-knesset

Asks your question to a council of LLMs. They answer independently, critique each other anonymously, then a chairman synthesizes a final answer.

Built on top of [Andrej Karpathy's llm-council](https://github.com/karpathy/llm-council) — the three-stage deliberation architecture is his work. This fork wraps it in a multi-user web app with Firebase auth, per-user model preferences, an admin panel, and SSE streaming.

---

## How it works

**Stage 1 — Responses**
All council members receive the query in parallel. Each answers without seeing the others.

**Stage 2 — Peer review**
Each model evaluates the other responses, anonymized as "Response A, B, C…" so they can't favor a known brand. They rank by accuracy and insight. The UI shows both the raw evaluation text and the extracted ranking so you can verify the system's interpretation.

**Stage 3 — Synthesis**
The chairman model reads all responses and rankings, then writes a final answer. Not a vote — a synthesis.

Every stage is inspectable.

---

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, Python 3.10+, async httpx |
| Frontend | React + Vite |
| Auth | Firebase (Google OAuth) |
| Storage | PostgreSQL |
| Models | OpenRouter (any model it carries) |

---

## Setup

**Prerequisites**: Python 3.10+, Node.js, PostgreSQL, OpenRouter API key with funded credits, Firebase project with Google auth enabled.

```bash
git clone https://github.com/aohana182/llm-knesset
cd llm-knesset

# backend
cp .env.example .env   # fill in all vars (see below)
uv sync
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001

# frontend (separate terminal)
cd frontend
npm install
npm run dev            # http://localhost:5173
```

Production (backend serves built frontend):

```bash
cd frontend && npm run build && cd ..
bash start.sh          # port 8080
```

---

## Environment variables

```
OPENROUTER_API_KEY=sk-or-...
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SESSION_SECRET=<long random string>

VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_API_KEY=AIza...
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
FIREBASE_CLIENT_EMAIL=firebase-adminsdk-...@your-project.iam.gserviceaccount.com
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
```

---

## Model configuration

Edit `backend/config.py` to set which models form the council and which acts as chairman. Any model available on OpenRouter works.

Override per-user in the UI, or system-wide through the admin panel. First user to sign in becomes admin.

---

## Tests

```bash
uv run pytest
```

---

## Credits

Three-stage deliberation concept and core architecture: [Andrej Karpathy](https://github.com/karpathy/llm-council).
