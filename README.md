# PP7-QA

**AI-powered compliance auditing for ProPresenter 7.**

PP7-QA is a self-hosted web app that connects to ProPresenter 7 via its REST API, lets you define reusable QA rules (with natural language AI assistance), audits your presentations against those rules, and automatically corrects violations — iterating until you are satisfied with compliance.

---

## Quick Start

### Prerequisites

| Requirement | Notes |
|---|---|
| Docker + Docker Compose | v24+ recommended |
| [Ollama](https://ollama.com) | Installed and running natively on your Mac |
| ProPresenter 7 | Running with its API enabled (see below) |

### Automated setup (recommended)

The easiest way to get started is the **GUI launcher** — a graphical app for installing prerequisites, starting/stopping containers, and monitoring status. It requires Python 3.9+ (standard on macOS, downloadable on Windows).

**macOS / Linux:**
```bash
git clone <repo>
cd pp7-qa
chmod +x launcher.sh setup.sh start.sh stop.sh
./launcher.sh
```

**Windows (PowerShell):**
```powershell
git clone <repo>
cd pp7-qa
.\launcher.ps1
```

The GUI launcher replaces `setup.*`, `start.*`, and `stop.*` for day-to-day use. The shell scripts remain available for headless/CI use.

### Manual setup

#### 1 — Enable the ProPresenter 7 API

In ProPresenter: **Preferences → Network → Enable Network API**  
Default host: `localhost`, default port: `50001` (as per the [official PP7 API docs](https://openapi.propresenter.com/)).

#### 2 — Pull an AI model

```bash
# Recommended for speed on Apple Silicon (3 GB RAM)
ollama pull llama3.2:3b

# Alternative for better reasoning (4.1 GB RAM)
ollama pull mistral:7b
```

#### 3 — Configure and start

```bash
cp .env.example .env   # copy defaults
docker compose up --build
```

The app is now available at **http://localhost:3000**  
FastAPI docs: **http://localhost:8000/docs**

---

## Scripts

All scripts live at the project root. Shell scripts require `chmod +x` on first use.

### `launcher.py` + `launcher.sh` / `launcher.ps1` — GUI Launcher ⭐

A graphical interface (Python + tkinter, no extra installs) with three tabs:

| Tab | Contents |
|---|---|
| **Setup** | Prerequisite status indicators, install buttons (Homebrew/winget), model selection + pull, `.env` creation |
| **Launch** | Config form (model, memory limits, ports, detach/rebuild toggles), Start / Stop / Stop+Reset buttons, browser quick-links |
| **Status** | Live container table (name, state, ports), refresh, view logs |

A persistent **Output Log** pane at the bottom streams all command output in real time.

**Requires:** Python 3.9+ (bundled on macOS, standard download on Windows). Uses only stdlib — no `pip install` needed.

### `setup.sh` / `setup.ps1`

Run once before the first launch. Checks and installs prerequisites.

| What it checks | Action if missing |
|---|---|
| Homebrew (macOS) | Offers to install |
| Docker Desktop | Offers to install via Homebrew/winget |
| Docker Compose | Verifies bundled with Docker Desktop |
| Ollama | Offers to install via Homebrew/winget |
| Ollama service | Attempts to start; warns if it can't |
| AI model | Interactive menu — pull one of 3 model options |
| `.env` file | Creates from `.env.example` if absent |

### `start.sh` / `start.ps1`

Starts the app. Runs interactively if no flags are given (prompts for settings with current values pre-filled).

**macOS / Linux:**
```bash
./start.sh                          # interactive prompts
./start.sh -d                       # background (detached)
./start.sh --build                  # force image rebuild
./start.sh --model mistral:7b       # change AI model
./start.sh --api-memory 2g          # increase API memory limit
./start.sh --frontend-memory 512m
./start.sh --api-port 8001 --frontend-port 3001
./start.sh --status                 # show container status
```

**Windows (PowerShell):**
```powershell
.\start.ps1                             # interactive prompts
.\start.ps1 -Detach                     # background (detached)
.\start.ps1 -Build                      # force image rebuild
.\start.ps1 -Model mistral:7b           # change AI model
.\start.ps1 -ApiMemory 2g              # increase API memory limit
.\start.ps1 -FrontendMemory 512m
.\start.ps1 -ApiPort 8001 -FrontendPort 3001
.\start.ps1 -Status                     # show container status
```

All options are persisted to `.env` so the next run remembers them.

### `stop.sh` / `stop.ps1`

Stops the containers. Data (rules, profiles, settings) is preserved by default.

```bash
./stop.sh               # stop, keep data
./stop.sh --clean       # stop AND delete database (irreversible!)
./stop.sh --prune       # stop + remove unused Docker images (free disk)
./stop.sh --status      # show container status
```

```powershell
.\stop.ps1              # stop, keep data
.\stop.ps1 -Clean       # stop AND delete database
.\stop.ps1 -Prune       # stop + remove unused Docker images
.\stop.ps1 -Status      # show container status
```

---

All settings can be changed via **Settings** in the app UI — changes persist to the database immediately.

Environment variables (`.env`) are startup defaults only:

| Variable | Default | Description |
|---|---|---|
| `PROPRESENTER_URL` | `http://host.docker.internal` | PP7 host. `host.docker.internal` resolves to your Mac from inside Docker. |
| `PROPRESENTER_PORT` | `50001` | PP7 API port (official default). |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Ollama API URL. Runs natively on Mac host for GPU acceleration. |
| `OLLAMA_MODEL` | `llama3.2:3b` | Model name — must already be pulled. |
| `FRONTEND_PORT` | `3000` | UI port. |
| `API_PORT` | `8000` | Backend API port. |

### Other platforms

**Linux / Windows with NVIDIA GPU:** Uncomment the `ollama` service in `docker-compose.yml` and set `OLLAMA_URL=http://ollama:11434`.

**Windows without GPU:** Keep Ollama running on the host; change `OLLAMA_URL` to `http://host.docker.internal:11434`.

---

## Workflow

### Create QA Rules

Three ways:

1. **AI Chat** — Describe your rule in plain English. The AI parses your intent and presents a structured rule for one-click saving.
2. **Form** — Use the Rules page to build a rule with field / operator / value selectors.
3. **Profile** — Group rules into named collections (e.g. _Sunday Service_, _Main Stage_).

### Run an Audit

Go to **Audit**, choose a profile or individual rules, and click **Run Audit**.

Results show:
- ✅ **Pass** — item is compliant
- ❌ **Fail** — item violates the rule; fix available or manual
- ⏭ **Skipped** — rule not applicable to this item

### Fix Violations

Select individual failing items (or click **Fix All**) and click **Fix**. The app calls the PP7 API to correct each item, then automatically re-runs the audit.

Repeat until the compliance report is acceptable.

---

## Rule Reference

### Target types

| Target | PP7 objects checked |
|---|---|
| `presentation` | Each presentation in all playlists |
| `slide` | Each cue/slide within presentations |
| `look` | All configured audience looks |
| `theme` | All configured themes |
| `prop` | All props |
| `macro` | All macros |
| `message` | All messages |

### Condition operators

| Operator | Description |
|---|---|
| `equals` | Exact match (case-insensitive string, or number/bool) |
| `not_equals` | Not an exact match |
| `contains` | Substring match or list membership |
| `not_contains` | Inverse of contains |
| `exists` | Field is present, non-null, and non-empty |
| `not_exists` | Field is absent, null, or empty |
| `matches_regex` | Python `re.search` match on the field value |

### Fix action types

| Type | Description |
|---|---|
| `noop` | No automatic fix — manual correction required |
| `set_field` | Sets a specific field value on the item via PP7 API |
| `trigger_look` | Calls `GET /v1/look/{id}/trigger` |
| `assign_theme` | Documents the required theme (full auto-assign requires PP7 UI) |

---

## Project Structure

```
pp7-qa/
├── docker-compose.yml       # Two services: api + frontend
├── .env.example             # Default configuration template
├── .env                     # Your local overrides (git-ignored)
├── README.md                # This file
├── ARCHITECTURE.md          # System design and service map
├── docs/
│   ├── phase2-import-feature.md   # Design spec for Word/PDF import (Phase 2)
│   └── api-reference.md           # PP7 API endpoint coverage reference
├── backend/                 # FastAPI application (Python 3.11)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py          # App entry point, router registration
│       ├── config.py        # Pydantic Settings (env vars)
│       ├── database.py      # SQLite + SQLAlchemy setup
│       ├── models/          # ORM models: config, rule, profile
│       ├── schemas/         # Pydantic schemas for API contracts
│       ├── routers/         # FastAPI route handlers
│       └── services/        # Business logic services
├── frontend/                # Next.js 15 application (TypeScript)
│   ├── Dockerfile
│   ├── src/app/             # App Router pages
│   └── src/lib/api.ts       # API client
└── data/                    # Volume-mounted SQLite database (git-ignored)
```

---

## Development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./pp7qa.db uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Roadmap

- **Phase 1** (current): Core QA engine — rules, profiles, audit, AI chat, auto-fix
- **Phase 2** (planned): Word/PDF import → auto-create presentations — see [docs/phase2-import-feature.md](docs/phase2-import-feature.md)

---

## Technical Notes

- **Apple Silicon**: Ollama runs natively on the Mac host for Metal GPU acceleration. Docker on macOS cannot pass through the Apple Silicon GPU, so keeping Ollama outside Docker is both faster and simpler.
- **Audit state**: The last audit run is cached in the API process memory (not the DB). If the API restarts, you must re-run the audit before applying fixes. This is intentional for Phase 1 simplicity.
- **PP7 write operations**: Some PP7 API fields are read-only or require UI interaction (e.g. full theme reassignment). These are marked as `manual fix` in the audit results.
