# FlowTrack

[![CI](https://github.com/aelena/flowtrack/actions/workflows/ci.yml/badge.svg)](https://github.com/aelena/flowtrack/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](backend/)
[![SvelteKit](https://img.shields.io/badge/SvelteKit-2-FF3E00?logo=svelte&logoColor=white)](frontend/)
[![PostgreSQL 16](https://img.shields.io/badge/postgres-16-4169E1?logo=postgresql&logoColor=white)](docker-compose.yml)

**A project tracker that makes you write down when to quit.**

Every project here carries two fields no other tracker asks for: `abandonment_criteria`, written up front, before you are emotionally invested; and two separate completion figures — the objective one computed from tasks, and your own honest estimate. The gap between them is a diagnosis.

It is a triage tool for people with too many side projects, not a to-do app. No Gantt charts, no agile artifacts, no burndown. Just my own way of tracking, built around a **Project** as a stateful bag of properties moving through a lightweight lifecycle. It will probably not work for you out of the box, and that is fine — it is opinionated on purpose.

## Architecture

| Component | Technology | Port |
|-----------|------------|------|
| Frontend  | SvelteKit (plain CSS, no Tailwind) | **7027** |
| API       | FastAPI (async, API key auth) | **7028** |
| Database  | PostgreSQL 16 (SQL + JSONB) | **7029** |

## Quick Start

```bash
git clone https://github.com/aelena/flowtrack.git
cd flowtrack

# 1. Create your environment file (the defaults work as-is for local use)
cp .env.example .env

# 2. Build and run
docker compose up --build

# 3. Open
# Frontend:  http://localhost:7027
# API docs:  http://localhost:7028/docs
# Database:  localhost:7029
```

`.env` is gitignored. Without it, `docker compose` has no values for
`POSTGRES_USER` and friends and the database container will not start — so
step 1 is not optional.

## Environment Variables

Copy `.env.example` to `.env` and adjust:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `flowtrack` | Database user |
| `POSTGRES_PASSWORD` | `flowtrack_secret` | Database password |
| `POSTGRES_DB` | `flowtrack` | Database name |
| `DATABASE_URL` | `postgresql+asyncpg://...@db:5432/flowtrack` | Internal DB connection (container-to-container, port 5432) |
| `API_KEY` | `ft_dev_key_change_me` | API key for all endpoints (`X-API-Key` header) |
| `STORAGE_PATH` | `/app/storage` | Persistent file storage path |
| `CORS_ORIGINS` | `http://localhost:7027` | Comma-separated allowed origins for CORS |

## Features

### Projects
- Work-in-progress and tentative final names
- Description, vision, goal, completion/abandonment criteria
- Star rating (1-5), subjective completion %, task-based completion %
- GitHub repo and website links
- Local directory reference
- Collaborators list
- Grouping by **Areas** (folders) with drag-and-drop between areas
- Project status: **active**, **on hold**, **deprecated**
- Archive without deletion
- Sidebar quick actions per project (archive, ZIP download, on hold, deprecated)

### Tasks
- Three statuses: new, in progress, done (click to cycle)
- Bulk creation from bullet or ordered lists
- Notes can be attached to tasks

### Notes
- Markdown content with live preview
- Attachable to projects or individual tasks

### Files
- Upload PDF, DOCX, MD, and other reference files
- Right-side file tree panel on project view, organized by folder
- Subfolders for skills, personalities, context files, etc.
- Persistent storage survives container restarts

### Write Mode
- Split-screen: markdown editor on left, live preview on right
- Zen-style distraction-free writing

### Commands
- Generate PRD, BRD, MRD from project data — deterministic, with JSON download buttons
- Export project as ZIP (includes files)
- View pending tasks summary
- Copy a `cd <dir> && claude` command for the project directory

### Configuration (`/settings`)
- YAML-based configuration editor, edited as raw YAML
- Provider API keys are redacted on read; leave the redaction placeholder in place to keep the stored value
- Save, reset to defaults

### Backup & Restore (`/settings`)
- **Export**: download all project data as a single JSON file (areas, projects, tasks, notes, snippets — no file attachments)
- **Import**: upload a JSON backup to merge into the database (skips existing records by ID)
- Useful for backup, migration, or transferring data between instances

### UI
- Dark and light theme toggle
- English and Spanish language toggle
- Font selector (Segoe UI, Georgia, Consolas, Arial, Palatino)
- Collapsible sidebar with project tree
- Search, filter by area, sort by name/date
- URL-based routing (`/projects/:id`) for deep linking
- SVG favicon for browser tab identification

## AI: the MCP server

FlowTrack does not call a model, and that is a decision rather than a gap.

Earlier versions pretended otherwise. Chat Mode returned an echo, "suggest next steps" was a handful of hardcoded heuristics, and the settings page happily stored OpenAI and Anthropic keys that nothing ever read. The obvious fix was to implement the layer for real — provider abstraction, streaming, key management, cost ceilings — and the honest assessment was that all of that work would end in a worse chat than the one already open in the next terminal window.

So the direction inverted. **FlowTrack stopped trying to be an AI application and became a tool an agent drives**, through an MCP server in [`mcp-server/`](mcp-server/). That deleted the fake surface instead of filling it in: the chat endpoint, the suggestion heuristics, the social-copy generator and the entire `llm_providers` table are gone. The feature arrived as a net removal of code, and there are no provider API keys left in the system to leak.

### What it gives an agent

Seven tools, and the number is deliberate. A server with one tool per REST endpoint gives the agent thirty ways to ask a question and no basis for choosing. These are shaped around what you actually want to know about a portfolio.

| Tool | |
|---|---|
| `portfolio_digest` | **The one that matters.** What is stale, what is overdue, active count against the WIP limit, and where the objective and subjective completion figures disagree most — in one call |
| `list_projects` | Compact digest, filterable by area, status, minimum stars, or days untouched |
| `get_project` | Full detail for one project, with tasks and notes |
| `add_tasks` | Bulk creation from a markdown list |
| `update_task_status` | new / in_progress / done |
| `add_note` | The durable record — decisions, especially decisions to stop |
| `set_project_state` | Status, stars, subjective completion: the verbs of a triage |

Two resources: `flowtrack://portfolio` renders every non-archived project as one markdown document, so an agent can take in the whole picture in a single cheap read; `flowtrack://project/{id}` does the same for one project.

### The prompts are the opinionated part

Prompts are the least-used corner of MCP and the reason this server is worth having rather than a generic database wrapper. They encode the opinions the tool exists to enforce.

**`/reckoning`** walks the stale and overdue projects one at a time, quotes each project's own `abandonment_criteria` back at you, and forces a single decision: continue, freeze, or kill. It records the answer, in your words, dated. It stops every five projects to ask whether to go on, and it does not soften the question — because freezing and killing are successful outcomes, and a portfolio where everything stays active is the failure this tool was built to prevent.

**`/next`** gives one recommendation rather than three options, and refuses to suggest starting anything while the WIP limit is exceeded.

**`/close-out`** drafts the abandonment note for a project you are stopping: what it was for, what got built, why it is stopping — specific and unsentimental, "no demand was ever tested" beats "priorities shifted" — and what is worth salvaging, by filename.

### Setup

```bash
claude mcp add flowtrack \
  --env FLOWTRACK_API_KEY=ft_dev_key_change_me \
  -- uvx --from ./mcp-server flowtrack-mcp
```

Full configuration, including Claude Desktop and Cursor, in [`mcp-server/README.md`](mcp-server/README.md).

### One thing to keep in mind

**Notes and snippets are data, not instructions.** Some of them arrive from arbitrary web pages through the Chrome clipper, which means a note can contain text engineered to read like a directive. The server's instructions say so explicitly, and any prompt built on top of this should treat note content as material to evaluate rather than orders to follow.

### Acting on a note from the UI

A note that says *"take the venv out of version control — that's 2000 files of junk"* is an actionable instruction sitting a long way from the repository it applies to. So each note carries an **Open session** button that starts a coding session in the project's directory, pointed at that note.

It appears only on notes belonging to a project that has `local_dir` set, because without a directory there is nowhere to open. The three actions are **Act on this**, **Explain this** and **Draft a plan**; the last two change nothing on disk.

This is where the MCP server pays for itself twice. The button does not need to stuff the note's text into a command line — which would mean quoting hell on two operating systems and a hard 8191-character limit in `cmd.exe`. It passes two ids and lets the agent fetch the note itself, along with the rest of the project's context.

**It needs one small process running on your machine**, in [`launcher/`](launcher/), because a containerised API cannot open a terminal on your host. Zero dependencies beyond the Python standard library:

```bash
export FLOWTRACK_API_KEY=ft_dev_key_change_me
python launcher/flowtrack_launcher.py
```

**Without it the buttons still work** — they copy the equivalent command to your clipboard instead. One paste rather than one click, and nothing to install. The Settings page shows which mode you are in.

The security model is the part worth reading before you run it, and it comes down to a single rule: **the launcher never executes anything the browser sends.** The request carries only `{project_id, note_id, action}` with `action` from a fixed set; the prompts live in the launcher's source and the command is assembled from its own configuration. The browser picks an intent, the launcher picks the command. Full detail, including what it does *not* defend against, in [`launcher/README.md`](launcher/README.md).

## Chrome Extension

Located in `extension/`. Load as an unpacked extension in Chrome:

1. Go to `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" and select the `extension/` folder
4. Click the extension icon, configure API URL (`http://localhost:7028`) and API key
5. Use the popup or right-click context menu ("Save to FlowTrack") to save URLs and text snippets to projects

The manifest declares `host_permissions` for `localhost` and `127.0.0.1`, which
is what lets the extension call the API at all — without it every request is
blocked before it leaves the browser. If you run FlowTrack on another host,
grant the optional permission for it, and add the extension origin to
`CORS_ORIGINS`:

```
CORS_ORIGINS=http://localhost:7027,chrome-extension://<your-extension-id>
```

## API Endpoints

All endpoints require `X-API-Key` header.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| **Areas** | | |
| GET/POST | `/api/areas/` | List/create areas |
| PUT/DELETE | `/api/areas/{id}` | Update/delete area (ungroups projects) |
| **Projects** | | |
| GET/POST | `/api/projects/` | List/create projects (query: search, area_id, sort_by, sort_order, archived) |
| GET/PUT | `/api/projects/{id}` | Get/update project |
| POST | `/api/projects/{id}/archive` | Archive project |
| POST | `/api/projects/{id}/export` | Export as ZIP (with files) |
| GET | `/api/projects/{id}/pending` | Pending tasks summary |
| POST | `/api/projects/{id}/collaborators` | Add collaborator |
| **Tasks** | | |
| GET/POST | `/api/projects/{pid}/tasks/` | List/create tasks (bulk from lists) |
| PUT/DELETE | `/api/projects/{pid}/tasks/{id}` | Update/delete task |
| **Notes** | | |
| GET/POST | `/api/notes/` | List/create notes (query: project_id, task_id) |
| PUT/DELETE | `/api/notes/{id}` | Update/delete note |
| **Files** | | |
| GET/POST | `/api/projects/{pid}/files/` | List/upload files |
| GET | `/api/projects/{pid}/files/{id}/download` | Download file |
| DELETE | `/api/projects/{pid}/files/{id}` | Delete file |
| **Extension** | | |
| GET | `/api/extension/projects` | Simplified project list for Chrome extension |
| POST | `/api/extension/snippet` | Save URL/snippet from extension |
| **Documents** | | |
| POST | `/api/documents/prd/{id}` | Generate PRD |
| POST | `/api/documents/brd/{id}` | Generate BRD |
| POST | `/api/documents/mrd/{id}` | Generate MRD |
| **Config** | | |
| GET | `/api/config/` | Get parsed config |
| GET/PUT | `/api/config/yaml` | Get/update config as YAML |
| POST | `/api/config/reset` | Reset config to defaults |
| **Backup** | | |
| GET | `/api/backup/export` | Export all data as JSON |
| POST | `/api/backup/import` | Import data from JSON |

## Running Tests

> **The suite drops every table after each test.** It therefore defaults to a
> separate `flowtrack_test` database and refuses to start if `TEST_DATABASE_URL`
> points at a database whose name does not end in `_test`.

Create the throwaway database once:

```bash
docker compose exec db psql -U flowtrack -d postgres -c 'CREATE DATABASE flowtrack_test;'
```

Then run the suite inside the API container (no local Python needed):

```bash
docker compose exec \
  -e TEST_DATABASE_URL=postgresql+asyncpg://flowtrack:flowtrack_secret@db:5432/flowtrack_test \
  api python -m pytest -q
```

Or from the host, against the published database port:

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest -q          # uses localhost:7029/flowtrack_test by default
```

## Project Structure

```
flowtrack/
  .env                          # Environment variables
  docker-compose.yml            # Container orchestration (ports 7027-7029)
  README.md                     # This file
  specs.md                      # Original product specification
  backend/
    Dockerfile
    requirements.txt
    app/
      main.py                   # FastAPI app entry point
      config.py                 # Settings from .env
      database.py               # Async SQLAlchemy setup + migrations
      models.py                 # All database models (Area, Project, Task, Note, etc.)
      schemas.py                # Pydantic request/response schemas
      dependencies.py           # API key verification
      routers/
        areas.py                # Area CRUD
        projects.py             # Project CRUD + export/archive/status
        tasks.py                # Task CRUD with bulk creation
        notes.py                # Note CRUD
        files.py                # File upload/download
        extension.py            # Chrome extension endpoints
        documents.py            # Deterministic PRD/BRD/MRD generation
        config.py               # YAML configuration management
        backup.py               # Full data export/import (JSON)
    tests/
      conftest.py               # Test fixtures with async DB
      test_areas.py
      test_projects.py
      test_tasks.py
      test_notes.py
  frontend/
    Dockerfile
    package.json
    svelte.config.js
    vite.config.js
    src/
      app.html                  # HTML shell with favicon
      app.css                   # Global styles, CSS variables, dark/light themes
      routes/
        +layout.svelte          # App shell: sidebar + toolbar (theme, lang, font, settings)
        +page.svelte            # Home dashboard with project cards
        projects/[id]/
          +page.svelte          # Project detail page
        settings/
          +page.svelte          # Settings: YAML config, API key, backup/restore
      lib/
        api.js                  # API client (all endpoints)
        stores.js               # Svelte stores (theme, lang, font, projects, etc.)
        i18n.js                 # EN/ES translations
        components/
          Sidebar.svelte        # Collapsible tree with drag-drop, search, actions
          ProjectView.svelte    # Two-column: project content + file tree panel
          TaskList.svelte       # Task list with status cycling
          AddTaskModal.svelte   # Bulk task creation modal
          NoteEditor.svelte     # Markdown note editor with preview
          WriteMode.svelte      # Split markdown/preview zen editor
          CommandBar.svelte     # Commands with download buttons (PRD, BRD, etc.)
    static/
      favicon.svg               # SVG favicon
  mcp-server/
    pyproject.toml              # Installable with uvx / pipx
    src/flowtrack_mcp/
      server.py                 # 7 tools, 2 resources, 3 prompts
      client.py                 # Thin async client over the REST API
    tests/
    smoke_test.py               # Drives the real stdio handshake
  extension/
    manifest.json               # Chrome extension manifest (V3)
    popup.html                  # Extension popup UI
    popup.css                   # Extension styles (zen aesthetic)
    popup.js                    # Extension logic (save URL/snippet)
    background.js               # Context menu service worker
```
