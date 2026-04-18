# Order Supervisor

An AI-powered order supervision system that monitors e-commerce orders end-to-end, proactively communicates with fulfillment, payments, and logistics teams, and automatically completes itself when an order is delivered or a refund flow resolves.
The backend is a Python FastAPI service that runs a persistent Claude agent per order; the frontend is a Next.js 14 App Router dashboard for real-time monitoring and control.

---

## Prerequisites

| Requirement | Version |
|---|---|
| Python | 3.11 + |
| Node.js | 18 + |
| Supabase account | (free tier is sufficient) |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/order-supervisor.git
cd order-supervisor
```

### 2. Create a Supabase project

1. Go to [supabase.com](https://supabase.com) and create a new project.
2. In **Project Settings → Database**, copy the **Connection string** (URI format).
   It looks like: `postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres`

### 3. Configure environment variables

```bash
# Root-level (used as reference — backend and frontend each have their own)
cp .env.example .env
```

Edit `.env` and fill in at minimum:

```env
DATABASE_URL=postgresql+asyncpg://postgres:[password]@db.[ref].supabase.co:5432/postgres
ANTHROPIC_API_KEY=sk-ant-...
```

Also copy the frontend env file:

```bash
cp frontend/.env.local.example frontend/.env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000 (default is already correct)
```

### 4. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

> **Tip:** Use a virtual environment: `python -m venv .venv && source .venv/bin/activate`

### 5. Initialise the database

```bash
python -m backend.db.init_db
```

This applies `schema.sql` (creates tables + indexes) and `seed.sql` (inserts the default supervisor). Safe to re-run.

### 6. Start the backend

```bash
uvicorn backend.main:app --reload --port 8000
```

The API is now available at <http://localhost:8000>.  
Interactive docs: <http://localhost:8000/docs>

### 7. Start the frontend

Open a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

### 8. Open the app

Visit **<http://localhost:3000>**

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | asyncpg connection string (`postgresql+asyncpg://…`) |
| `ANTHROPIC_API_KEY` | ✅ | — | Anthropic API key |
| `CLASSIFIER_MODEL` | | `claude-haiku-4-5-20251001` | Model used for event triage |
| `MAIN_AGENT_MODEL` | | `claude-sonnet-4-6` | Model used for the supervisor agent |
| `MAX_RUN_AGE_HOURS` | | `72` | Runs older than this are auto-completed |
| `SCHEDULER_INTERVAL_SECONDS` | | `60` | How often the scheduler polls for sleeping runs |

### Frontend (`frontend/.env.local`)

| Variable | Required | Default | Description |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | | `http://localhost:8000` | Base URL of the FastAPI backend |

---

## API Endpoints

### Supervisors

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/supervisors` | Create a supervisor configuration |
| `GET` | `/api/supervisors` | List all supervisors |
| `GET` | `/api/supervisors/{id}` | Get a single supervisor |

### Runs

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/runs` | Create a run — starts agent in background |
| `GET` | `/api/runs` | List all runs (includes supervisor name) |
| `GET` | `/api/runs/{id}` | Full detail: run + activity log |
| `POST` | `/api/runs/{id}/events` | Inject an event — classifier decides whether to wake agent (202) |
| `POST` | `/api/runs/{id}/instructions` | Append an operator instruction |
| `POST` | `/api/runs/{id}/interrupt` | Set status → `interrupted` |
| `POST` | `/api/runs/{id}/pause` | Set status → `paused` |
| `POST` | `/api/runs/{id}/resume` | Set status → `running`, wake agent |
| `POST` | `/api/runs/{id}/terminate` | Set status → `terminated`, generate final summary |

### Meta

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |

---

## Project Structure

```
order-supervisor/
├── backend/
│   ├── agent/
│   │   ├── classifier.py   # Fast triage model — should we wake the agent?
│   │   ├── runtime.py      # Core agentic loop + complete_run()
│   │   ├── runner.py       # Thin adapter layer for FastAPI BackgroundTasks
│   │   └── tools.py        # Claude tool definitions (7 tools)
│   ├── db/
│   │   ├── database.py     # Async SQLAlchemy engine + get_db() dependency
│   │   ├── init_db.py      # One-shot DB init script
│   │   ├── schema.sql      # Table definitions + indexes
│   │   └── seed.sql        # Default supervisor seed
│   ├── routers/
│   │   ├── runs.py         # Run lifecycle endpoints
│   │   └── supervisors.py  # Supervisor CRUD
│   ├── config.py           # pydantic-settings — reads .env
│   ├── main.py             # FastAPI app + CORS + APScheduler lifespan
│   ├── models.py           # Pydantic request/response models
│   ├── scheduler.py        # APScheduler job: wake sleeping runs
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx              # Dashboard — runs list
│   │   ├── runs/[id]/page.tsx    # Run detail — log + controls
│   │   └── supervisors/page.tsx  # Supervisor management
│   ├── components/
│   │   ├── ActivityLogEntry.tsx  # Timeline entry component
│   │   ├── NewRunModal.tsx       # Create-run modal
│   │   └── StatusBadge.tsx       # Coloured status pill
│   ├── lib/
│   │   ├── api.ts    # Axios instance
│   │   └── types.ts  # Shared TypeScript types
│   └── package.json
├── .env.example
├── ARCHITECTURE.md
└── README.md
```
