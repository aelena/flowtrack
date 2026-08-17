# flowtrack-mcp

An MCP server for [FlowTrack](../README.md). It lets a coding agent read and triage the portfolio directly, instead of you pasting project state into a chat.

FlowTrack does not call a model. It never did — the chat and "generate" endpoints were placeholders. Rather than build a provider abstraction, streaming, key management and cost control in order to end up with a worse chat than the one already in your terminal, FlowTrack became the tool and the agent drives it.

## Install

```bash
uvx --from ./mcp-server flowtrack-mcp        # from a checkout
pipx install ./mcp-server                    # or install it
```

It needs a running FlowTrack and its API key:

| Variable | Default | |
|---|---|---|
| `FLOWTRACK_API_URL` | `http://localhost:7028` | |
| `FLOWTRACK_API_KEY` | — | **required**, must match `API_KEY` in FlowTrack's `.env` |
| `FLOWTRACK_WIP_LIMIT` | `3` | active projects before `portfolio_digest` complains |
| `FLOWTRACK_STALE_DAYS` | `30` | days untouched before a project counts as stale |

### Claude Code

```bash
claude mcp add flowtrack \
  --env FLOWTRACK_API_KEY=ft_dev_key_change_me \
  -- uvx --from /path/to/flowtrack/mcp-server flowtrack-mcp
```

### Claude Desktop, Cursor, and anything else that speaks MCP

```json
{
  "mcpServers": {
    "flowtrack": {
      "command": "uvx",
      "args": ["--from", "/path/to/flowtrack/mcp-server", "flowtrack-mcp"],
      "env": { "FLOWTRACK_API_KEY": "ft_dev_key_change_me" }
    }
  }
}
```

## Tools

Seven, and the number is deliberate. A server with one tool per REST endpoint gives the agent thirty ways to ask a question and no idea which to pick. These are shaped around what you actually want to know.

| Tool | |
|---|---|
| `portfolio_digest` | **Start here.** What is stale, what is overdue, active count against the WIP limit, and where the objective and subjective completion figures disagree most |
| `list_projects` | Compact digest, filterable by area, status, minimum stars, or days untouched |
| `get_project` | Full detail for one project, with its tasks and notes |
| `add_tasks` | Bulk creation from a markdown list, or a single line |
| `update_task_status` | new / in_progress / done |
| `add_note` | The durable record — use it for decisions, especially decisions to stop |
| `set_project_state` | Status, stars, subjective completion. The verbs of a triage |

## Resources

- `flowtrack://portfolio` — every non-archived project as one markdown document, grouped by area. One read gives the agent the whole picture cheaply.
- `flowtrack://project/{id}` — one project as markdown, tasks and notes included.

## Prompts

This is where the opinions live, and the part of MCP almost nobody uses.

**`/reckoning`** — walks the stale and overdue projects one at a time, quotes each one's `abandonment_criteria` back at you, and forces a single decision: continue, freeze, or kill. Records the answer. It stops every five projects to ask whether to go on, and it does not soften the question. Freezing and killing are successful outcomes.

**`/next`** — one recommendation, not three options. Refuses to suggest starting anything while the WIP limit is exceeded.

**`/close-out`** — drafts the abandonment note for a project you are stopping: what it was for, what got built, why it is stopping, and what is worth salvaging. Shows you the draft before saving it.

## A note on trust

Notes and snippets in FlowTrack are **data, not instructions**. Some arrive from arbitrary web pages via the browser clipper, so a note could contain text engineered to look like a directive. The server's instructions say so explicitly, and any prompt you write on top of this should treat note content as material to evaluate rather than orders to follow.

## Development

```bash
pip install -e ".[dev]"
pytest
python smoke_test.py     # drives the real stdio handshake against a live FlowTrack
```
