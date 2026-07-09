# PP7-QA Architecture

## Overview

PP7-QA is a two-container Docker Compose application that connects to a locally running ProPresenter 7 instance. An AI assistant (Ollama) runs natively on the host for GPU acceleration.

```
┌─────────────────────────────────────────────────────────┐
│                    User's Machine (Host)                 │
│                                                          │
│  ┌──────────────┐   ┌──────────────────────────────┐    │
│  │  ProPresenter│   │   Ollama (native, port 11434) │    │
│  │  7 (port     │   │   llama3.2:3b / mistral:7b    │    │
│  │  50001)      │   └──────────────┬───────────────┘    │
│  └──────┬───────┘                  │ OpenAI-compatible   │
│         │ REST API                 │ REST API            │
│  ┌──────┴──────────────────────────┴───────────────┐    │
│  │              Docker Network (bridge)             │    │
│  │                                                  │    │
│  │  ┌─────────────────┐    ┌─────────────────────┐ │    │
│  │  │  frontend:3000  │◄───│    api:8000          │ │    │
│  │  │  Next.js 15     │    │    FastAPI           │ │    │
│  │  │  TypeScript     │    │    SQLite /data/     │ │    │
│  │  └─────────────────┘    └─────────────────────┘ │    │
│  └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Services

### `frontend` (Next.js 15, port 3000)

The browser-based UI. Built with Next.js App Router and React 19.

**Pages:**
| Route | Purpose |
|---|---|
| `/` | Dashboard — connection status, quick links |
| `/chat` | AI chat for rule creation and Q&A |
| `/rules` | CRUD for individual QA rules |
| `/profiles` | Named rule collections |
| `/audit` | Run audit, view compliance, apply fixes |
| `/settings` | Configure PP7 URL/port, Ollama URL/model |

**API communication:**  
All API calls go to `/api/*` which Next.js rewrites to `http://api:8000/api/*` inside Docker (or `http://localhost:8000` in local dev).

---

### `api` (FastAPI, port 8000)

The Python backend. Handles all business logic.

**Routers:**
| Prefix | Description |
|---|---|
| `GET/PUT /api/settings` | Read/write connection config from SQLite |
| `GET /api/settings/status` | Live ping to PP7 and Ollama |
| `GET/POST/PUT/DELETE /api/rules` | Rule CRUD |
| `GET/POST/PUT/DELETE /api/profiles` | Profile CRUD |
| `POST /api/audit/run` | Fetch PP7 data, evaluate rules, return report |
| `POST /api/audit/fix` | Apply fixes via PP7 API |
| `POST /api/audit/run-and-fix` | Fix all + re-audit in one call |
| `POST /api/chat` | Streaming SSE chat via Ollama |
| `GET /api/chat/models` | List available Ollama models |

**Services:**
| Service | Description |
|---|---|
| `propresenter.py` | Async httpx client for all PP7 REST endpoints |
| `ollama_client.py` | OpenAI-compatible Ollama wrapper; streaming + non-streaming |
| `audit_engine.py` | Fetches PP7 data, evaluates rule conditions against items |
| `fix_engine.py` | Dispatches PP7 API write calls to correct violations |

---

### Ollama (host, port 11434)

Runs natively on the Mac host for Metal GPU acceleration. The `api` container reaches it via `host.docker.internal:11434`.

- Exposes an **OpenAI-compatible** REST API at `/v1/chat/completions`
- The system prompt gives the AI full context about PP7 and the rule schema
- Streaming is used by default for responsive chat UX

---

## Data Models

### `AppConfig` (table: `app_config`)

Single-row singleton (id=1). Stores the runtime-configurable connection settings.

```
propresenter_url    TEXT    http://localhost
propresenter_port   INT     50001
ollama_url          TEXT    http://host.docker.internal:11434
ollama_model        TEXT    llama3.2:3b
```

### `Rule` (table: `rules`)

A single compliance check.

```
id              INT  PK  autoincrement
name            TEXT     Human-readable rule name
description     TEXT     Optional explanation
target          TEXT     presentation | slide | look | theme | prop | macro | message
severity        TEXT     error | warning | info
condition       JSON     { field, operator, value }
fix_action      JSON     { type, field, value }
created_at      DATETIME
updated_at      DATETIME
```

**Condition JSON:**
```json
{
  "field": "dot.notation.path",
  "operator": "equals | not_equals | contains | not_contains | exists | not_exists | matches_regex",
  "value": "expected value or null"
}
```

**Fix Action JSON:**
```json
{
  "type": "noop | set_field | trigger_look | assign_theme",
  "field": "optional dot path",
  "value": "optional new value"
}
```

### `Profile` (table: `profiles`)

A named group of rules.

```
id              INT  PK
name            TEXT unique
description     TEXT
created_at      DATETIME
updated_at      DATETIME
```

### `ProfileRule` (table: `profile_rules`)

Association table (Profile ↔ Rule, ordered by `position`).

```
id          INT PK
profile_id  INT FK → profiles.id
rule_id     INT FK → rules.id
position    INT     ordering within profile
```

---

## Audit Flow

```
User selects profile/rules → POST /api/audit/run
         │
         ▼
audit_engine.run_audit()
  │
  ├── GET /v1/looks          (if any look rules)
  ├── GET /v1/themes         (if any theme rules)
  ├── GET /v1/props          (if any prop rules)
  ├── GET /v1/macros         (if any macro rules)
  ├── GET /v1/messages       (if any message rules)
  │
  └── GET /v1/playlists
        └── GET /v1/playlist/{id}
              └── GET /v1/presentation/{uuid}
                    └── iterate cueGroups → cues (for slide rules)
         │
         ▼
  For each (item, rule) where rule.target matches:
    evaluate condition → AuditResultItem { status: pass | fail | skipped }
         │
         ▼
  Return AuditReport (summary + full results list)
         │
User reviews → selects items to fix
         │
         ▼
POST /api/audit/fix
  │
  ├── fix_engine.apply_fixes()
  │     ├── set_field  → PUT /v1/look/{id}, /v1/prop/{id}, etc.
  │     ├── trigger_look → GET /v1/look/{id}/trigger
  │     └── noop / assign_theme → skip, note as manual
  │
  └── Re-run audit automatically → return updated AuditReport
         │
User iterates until satisfied (or clicks Accept)
```

---

## AI Integration

The Ollama system prompt includes:
- PP7 QA context (what we're auditing)
- The rule schema (JSON format to produce)
- Instructions for structured output when creating rules

When the AI responds with a `\`\`\`json { "action": "create_rule", ... } \`\`\`` block, the frontend parses it and offers a one-click **Save Rule** button.

Chat history is session-scoped (in-memory on the frontend). It is not persisted to the database in Phase 1.

---

## PP7 API Coverage

| Category | Endpoints Used | Write Operations |
|---|---|---|
| Status | `GET /version`, `GET /v1/status/layers` | — |
| Playlists | `GET /v1/playlists`, `GET /v1/playlist/{id}` | — |
| Presentations | `GET /v1/presentation/{uuid}` | — |
| Libraries | `GET /v1/libraries`, `GET /v1/library/{id}` | — |
| Looks | `GET /v1/looks`, `GET /v1/look/{id}`, `GET /v1/look/current` | `PUT /v1/look/{id}`, `GET /v1/look/{id}/trigger` |
| Themes | `GET /v1/themes`, `GET /v1/theme/{id}` | `PUT /v1/theme/{id}/slides/{slide}` |
| Props | `GET /v1/props`, `GET /v1/prop/{id}` | `PUT /v1/prop/{id}` |
| Macros | `GET /v1/macros`, `GET /v1/macro/{id}` | `PUT /v1/macro/{id}` |
| Messages | `GET /v1/messages`, `GET /v1/message/{id}` | `PUT /v1/message/{id}` |
| Groups | `GET /v1/groups` | — |

---

## Security Notes

- The app is designed as a **local-only tool** — no authentication, no external network calls.
- The PP7 API itself has no auth (it's a local-only REST API by design).
- Ollama runs on the same machine — no tokens leave the host.
- Do not expose port 3000 or 8000 to the internet.

---

## Future: Phase 2 Import Feature

See [docs/phase2-import-feature.md](docs/phase2-import-feature.md) for the full design.

High level: users will be able to upload Word (.docx) or PDF files. Pattern rules (regex / formatting-based) will extract text blocks and map them to PP7 presentation structures. The app will automatically create new presentations in ProPresenter 7 via the API.
