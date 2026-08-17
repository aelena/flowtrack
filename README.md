# FlowTrack

Personal project tracking tool with a minimalistic, zen-style interface. Combines task management, note-taking, and AI-assisted workflows around the concept of a **Project** — a stateful bag of properties that transitions through a lightweight lifecycle. No Gantt BS, no agile artifacts, just my own way of tracking. Will probably not work for you of the box.

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

### Chat Mode
- ChatGPT-style interface for project-context conversations
- Connects to configured LLM providers (BYOK)

### Commands
- Generate PRD, BRD, MRD from project data — with JSON download buttons
- Generate social media content (LinkedIn, Twitter)
- Suggest next steps and ideas
- Export project as ZIP (includes files)
- Open Claude CLI on project directory
- View pending tasks summary

### Configuration (`/settings`)
- YAML-based configuration editor for:
  - **LLM providers**: OpenAI, Anthropic, Ollama (local), custom endpoints
  - **IDE executables**: Cursor, VS Code, WebStorm — with `{project_dir}` placeholder
  - **CLI settings**: Claude command path
- Save, reset to defaults
- API key management

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
| **LLM** | | |
| GET/POST | `/api/llm/providers` | List/add LLM providers |
| POST | `/api/llm/generate/prd/{id}` | Generate PRD |
| POST | `/api/llm/generate/brd/{id}` | Generate BRD |
| POST | `/api/llm/generate/mrd/{id}` | Generate MRD |
| POST | `/api/llm/generate/social/{id}` | Generate social content |
| POST | `/api/llm/chat/{id}` | Chat with project context |
| POST | `/api/llm/suggest/{id}` | Suggest next steps |
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
        llm.py                  # LLM integration + document generation
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
          ChatMode.svelte       # ChatGPT-style chat interface
          CommandBar.svelte     # Commands with download buttons (PRD, BRD, etc.)
    static/
      favicon.svg               # SVG favicon
  extension/
    manifest.json               # Chrome extension manifest (V3)
    popup.html                  # Extension popup UI
    popup.css                   # Extension styles (zen aesthetic)
    popup.js                    # Extension logic (save URL/snippet)
    background.js               # Context menu service worker
```
