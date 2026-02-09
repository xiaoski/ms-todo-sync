# ms-todo-sync

A command-line client for **Microsoft To Do**, built on [Microsoft Graph API](https://learn.microsoft.com/en-us/graph/api/resources/todo-overview).

It works in two ways:

- 🤖 **As an AI Agent Skill** — Drop it into [Claude Code](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview), [Cline](https://github.com/cline/cline) or any agent that supports the SKILLS convention, and let the AI manage your tasks.
- 🖥️ **As a standalone CLI** — Use the script directly in your terminal for quick task management.

## Features

- 📋 **List & Task CRUD** — Create, view, delete task lists and tasks
- 🔍 **Search & Filter** — Full-text search, today/overdue/pending views
- ⭐ **Priority & Due Dates** — Set importance and deadlines
- 📊 **Statistics** — Completion rate, overdue count, etc.
- 📤 **Export** — Dump all tasks to JSON
- 🔐 **Device Code Auth** — Non-blocking two-step login, agent-friendly

## Prerequisites

- **Python >= 3.9**
- **[uv](https://docs.astral.sh/uv/)** — Fast Python package manager (`pip install uv`)

## Quick Start

### 1. Clone

```bash
git clone https://github.com/<your-username>/ms-todo-sync.git
cd ms-todo-sync
```

### 2. Login

A two-step device code flow — no need to register your own Azure app:

```bash
# Step 1: Get a verification code
uv run scripts/ms-todo-sync.py login get

# You'll see a URL and a code. Open the URL in your browser,
# enter the code, and sign in with your Microsoft account.

# Step 2: Complete login
uv run scripts/ms-todo-sync.py login verify
```

The token is cached to `~/.mstodo_token_cache.json` — you won't need to log in again unless you explicitly log out.

### 3. Use

```bash
# List all task lists
uv run scripts/ms-todo-sync.py lists

# Add a task
uv run scripts/ms-todo-sync.py add "Buy groceries" -l "Shopping" -p high -d 2

# View all pending tasks grouped by list
uv run scripts/ms-todo-sync.py pending -g

# Mark a task as done
uv run scripts/ms-todo-sync.py complete "Buy groceries" -l "Shopping"

# Search across all lists
uv run scripts/ms-todo-sync.py search "report"
```

## Command Overview

| Command | Description |
|---------|-------------|
| `lists` | List all task lists |
| `create-list` | Create a new list |
| `delete-list` | Delete a list |
| `tasks` | List tasks in a list |
| `add` | Add a new task |
| `complete` | Mark a task as done |
| `delete` | Delete a task |
| `detail` | View task details (fuzzy match) |
| `search` | Search tasks by keyword |
| `pending` | Show all incomplete tasks |
| `today` | Tasks due today |
| `overdue` | Overdue tasks |
| `stats` | Task statistics |
| `export` | Export to JSON |
| `login get/verify` | Two-step authentication |
| `logout` | Clear cached tokens |

Run `uv run scripts/ms-todo-sync.py --help` for full details, or see [SKILL.md](SKILL.md) for the complete reference.

## Use as an AI Agent Skill

This project follows the **SKILLS convention** — the [SKILL.md](SKILL.md) file contains everything an AI agent needs to discover and use this tool: command signatures, parameter tables, output formats, error handling, and agent-specific guidelines.

### Setup for Claude Code

Add the skill directory to your Claude Code configuration:

```bash
# In your Claude Code project, add this repo as a skill:
claude mcp add-skill /path/to/ms-todo-sync
```

Or simply point your agent to the directory containing `SKILL.md`. The agent will automatically:

1. Detect the skill and read its capabilities
2. Handle authentication by presenting the login URL to you
3. Execute task operations based on your natural language requests

### Example agent interactions

> "Show me all my overdue tasks"  
> "Add a high-priority task 'Prepare slides' to my Work list, due in 2 days"  
> "What's my task completion rate?"  
> "Mark 'Buy groceries' as done"

## Project Structure

```
ms-todo-sync/
├── SKILL.md              # AI Agent skill definition (the primary interface doc)
├── scripts/
│   └── ms-todo-sync.py   # Main CLI script
├── pyproject.toml         # Project metadata & dependencies
├── requirements.txt       # Pip-compatible dependencies
└── README.md              # This file
```

## License

MIT
