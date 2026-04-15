# ms-todo-sync

A command-line client for **Microsoft To Do**, built on [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/api/resources/todo-overview).

It works in two ways:

- 🤖 **As an AI Agent Skill** — Drop it into [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), [Cline](https://github.com/cline/cline) or any agent that supports the SKILLS convention, and let the AI manage your tasks.
- 🖥️ **As a standalone CLI** — Use the script directly in your terminal for quick task management.

## Features

- 📋 **List & Task CRUD** — Create, view, delete task lists and tasks
- 🔍 **Search & Filter** — Full-text search, filter by status (completed/incomplete), filter by date (created/due)
- ⭐ **Priority & Due Dates** — Set importance and deadlines with flexible date formats
- 📊 **Statistics** — Completion rate, overdue count, etc.
- 📤 **Export** — Dump all tasks to JSON
- 🔐 **Device Code Auth** — Non-blocking single-step login, agent-friendly
- 🤖 **Agent-Optimized** — JSON output with consistent structure, ID-based operations, proper error handling

## Prerequisites

- **Python >= 3.9**
- **[uv](https://docs.astral.sh/uv/)** — Fast Python package manager (`pip install uv`)

## Quick Start

### 1. Clone

```bash
git clone https://github.com/xiaoski/ms-todo-sync.git
cd ms-todo-sync
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Login

A single-step device code flow — no need to register your own Azure app:

```bash
uv run scripts/ms-todo-sync.py login
```

You'll see a URL and a verification code. Open the URL in your browser, enter the code, and sign in with your Microsoft account. Then press Enter in the terminal.

The token is cached to `~/.mstodo_token_cache.json` — you won't need to log in again unless you explicitly log out.

### 4. Use

```bash
# List all task lists
uv run scripts/ms-todo-sync.py list

# Add a task
uv run scripts/ms-todo-sync.py add "Buy groceries" -l "Shopping" -p high -d 2

# View all pending tasks grouped by list
uv run scripts/ms-todo-sync.py pending -g

# Mark a task as done
uv run scripts/ms-todo-sync.py done "Buy groceries" -l "Shopping"

# Search tasks
uv run scripts/ms-todo-sync.py find "report"

# Search with filters (incomplete, due this week)
uv run scripts/ms-todo-sync.py find --incomplete --due-after "2026-04-13" --due-before "2026-04-19"
```

## Command Overview

| Command | Description |
|---------|-------------|
| `list` / `ls` | List all task lists |
| `list add` | Create a new list |
| `list remove` | Delete a list |
| `show` / `tasks` | List tasks in a list |
| `add` / `new` | Add a new task |
| `done` / `complete` | Mark a task as done |
| `remove` / `rm` | Delete a task |
| `view` / `info` | View task details |
| `find` / `search` | Search and filter tasks |
| `pending` / `all` | Show all incomplete tasks |
| `today` | Tasks due today |
| `overdue` | Overdue tasks |
| `stats` | Task statistics |
| `export` | Export to JSON |
| `login` | Authentication |
| `logout` | Clear cached tokens |

Run `uv run scripts/ms-todo-sync.py --help` for full details, or see [SKILL.md](SKILL.md) for the complete reference.

## Agent Integration

This project follows the **SKILLS convention** — the [SKILL.md](SKILL.md) file contains everything an AI agent needs to discover and use this tool: command signatures, parameter tables, output formats, error handling, and agent-specific guidelines.

### Setup for Claude Code

Point your agent to the directory containing `SKILL.md`. The agent will automatically:

1. Detect the skill and read its capabilities
2. Handle authentication by presenting the login URL to you
3. Execute task operations based on your natural language requests

### Recommended Agent Workflow

```bash
# 1. Check current state
uv run scripts/ms-todo-sync.py -j pending          # Get JSON with all task IDs

# 2. Perform operations using IDs (more reliable)
uv run scripts/ms-todo-sync.py done <id>
uv run scripts/ms-todo-sync.py remove <id> -y

# 3. Search with filters
uv run scripts/ms-todo-sync.py find --incomplete --due-after "2026-04-01"
```

### JSON Output

All commands support `-j/--json` for structured output:

```json
{
  "success": true,
  "data": {
    "total": 5,
    "tasks": [
      {"id": "...", "title": "...", "status": "...", ...}
    ]
  },
  "message": null
}
```

## Project Structure

```
ms-todo-sync/
├── SKILL.md              # AI Agent skill definition (primary interface doc)
├── scripts/
│   └── ms-todo-sync.py   # Main CLI script
├── pyproject.toml         # Project metadata & dependencies
├── requirements.txt       # Pip-compatible dependencies
└── README.md              # This file
```

## License

MIT
