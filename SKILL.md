---
name: ms-todo-sync
description: >
  Microsoft To Do CLI tool (v2 optimized). Verb-noun command structure with short aliases, smart ID/title detection, quiet mode, and JSON output.
  Key commands: list/ls, add/new, done/complete, remove/rm, view/info, find/search, today, overdue, pending/all, login
example_prompts:
  - "List all my task lists"
  - "Add a task to buy milk to Shopping list"
  - "Show tasks due today"
  - "Mark a task as completed"
  - "Search for tasks containing 'meeting'"
  - "Search for incomplete tasks due this week"
metadata:
  version: 2.0.0
  author: xiaoski@qq.com
  license: MIT License
  tags: [productivity, task-management, microsoft-todo, cli]
  category: productivity
---

# ms-todo-sync (v2)

Microsoft To Do command-line client, manages tasks and lists via Microsoft Graph API.

**v2 New Features:**
- ✅ Unified verb-noun command structure
- ✅ Short aliases (`ls`, `rm`, `new`, etc.)
- ✅ Smart task detection (ID or title auto-recognition)
- ✅ Quiet mode (`-q/--quiet`) - ID only output
- ✅ JSON output (`-j/--json`) - Machine-readable, consistent structure
- ✅ More intuitive parameter names (`--note` instead of `--description`)
- ✅ Powerful search filters (by status, date filtering)

---

## AGENT Quick Start - MUST READ

### Command Cheat Sheet

| Goal | Command | Alias |
|------|---------|-------|
| View all lists | `uv run scripts/ms-todo-sync.py list` | `uv run scripts/ms-todo-sync.py ls` |
| Add task (default list) | `uv run scripts/ms-todo-sync.py add "task title"` | `uv run scripts/ms-todo-sync.py new` |
| Add task to list | `uv run scripts/ms-todo-sync.py add "task title" -l "list name"` | - |
| View all pending tasks | `uv run scripts/ms-todo-sync.py pending` | `uv run scripts/ms-todo-sync.py all` |
| View today's tasks | `uv run scripts/ms-todo-sync.py today` | - |
| View overdue tasks | `uv run scripts/ms-todo-sync.py overdue` | - |
| Search tasks | `uv run scripts/ms-todo-sync.py find "keyword"` | `uv run scripts/ms-todo-sync.py search` |
| Filter incomplete | `uv run scripts/ms-todo-sync.py find --incomplete` | - |
| Complete task | `uv run scripts/ms-todo-sync.py done <ID or title>` | `uv run scripts/ms-todo-sync.py complete` |
| Delete task (skip confirm) | `uv run scripts/ms-todo-sync.py remove <ID or title> -y` | `uv run scripts/ms-todo-sync.py rm` |

### Agent Recommended Workflow

Use ID-based operations for reliability:

```
1. cd <skill_directory> (must run all commands from SKILL.md directory)
2. Check dependencies: uv sync (run if ModuleNotFoundError occurs)
3. Verify login: uv run scripts/ms-todo-sync.py list
   - If "Not logged in" → run: uv run scripts/ms-todo-sync.py login
4. Get task IDs: uv run scripts/ms-todo-sync.py -q pending (quiet mode, ID only)
   or: uv run scripts/ms-todo-sync.py -j pending (JSON format with details)
5. Use ID for operations: uv run scripts/ms-todo-sync.py done <id>, uv run scripts/ms-todo-sync.py remove <id> -y, uv run scripts/ms-todo-sync.py view <id>
```

### Login Flow

```bash
uv run scripts/ms-todo-sync.py login
```

Single-step device code flow:
1. Display verification code and URL
2. Wait for user to complete in browser
3. Press Enter to confirm

**Note**: `login` is interactive - **do not use** with `-j` or `-q` options.

### Task Categorization Suggestions

Choose list based on context:
- Work-related → "Work" list
- Personal matters → "Personal" list
- Shopping items → "Shopping" list
- Project-specific → Use project name as list
- User unspecified → Default list

### Agent Key Rules

⚠️ **Global options must come before subcommand**: `-q/-j/-v/--debug` must precede the command, e.g. `uv run scripts/ms-todo-sync.py -j list`
⚠️ **Smart task detection**: `done`/`remove`/`view` auto-detect ID or title
⚠️ **Recommend ID usage**: Get ID first via `-q` or `-j`, then operate by ID
⚠️ **Quiet mode**: `-q` outputs ID only, good for scripts and pipes
⚠️ **JSON mode**: `-j` outputs structured data, recommended for agents
⚠️ **Delete operations**: `remove`/`rm-list` confirms by default, use `-y` to skip
⚠️ **Auto list creation**: Lists are auto-created if they don't exist when using `add`
⚠️ **login command**: Interactive command, do not use with `-j/-q`

---

## Prerequisites

1. **Python >= 3.9**
2. **[uv](https://docs.astral.sh/uv/)** - Python package manager: `pip install uv`
3. **Working directory**: All commands must run in the directory containing SKILL.md
4. **Network access**: Must access Microsoft Graph API
5. **Authentication**: First use requires browser-based interactive login

---

## Installation

### First Setup

```bash
cd <path-to-ms-todo-sync>
uv sync  # Install dependencies (recommended)
```

### Verify Installation

```bash
uv run scripts/ms-todo-sync.py --help
```

---

## Command Reference

All commands follow this format:

```
uv run scripts/ms-todo-sync.py [GLOBAL_OPTIONS] <command> [COMMAND_OPTIONS]
```

### Global Options

| Option | Description |
|--------|-------------|
| `-q, --quiet` | Quiet mode, output ID or errors only **must precede subcommand** |
| `-j, --json` | JSON output (machine-readable) **must precede subcommand**, recommended for agents |
| `-v, --verbose` | Show detailed info **must precede subcommand** |
| `--debug` | Enable debug mode **must precede subcommand** |

### JSON Output Format

All commands support `-j/--json` with unified output format:

```json
{
  "success": true,
  "data": { ... },
  "message": "optional message"
}
```

**data field structure by command**:

| Command | data field |
|---------|-----------|
| `list` | `{"total": N, "lists": [...]}` |
| `pending` | `{"total": N, "tasks": [...]}` |
| `today` | `{"total": N, "tasks": [...]}` |
| `overdue` | `{"total": N, "tasks": [...]}` |
| `find` | `{"keyword": "...", "filters": {...}, "total": N, "results": [...]}` |
| `show` | `{"list": "...", "includeCompleted": bool, "total": N, "tasks": [...]}` |
| `view` | The task object itself |
| `add` | The created task object |
| `done` | The completed task object |
| `remove` | The deleted task object |
| `list add` | The created list object |
| `stats` | Statistics object |

**Error response format**:
```json
{
  "success": false,
  "data": null,
  "message": "error description"
}
```

**Examples:**
```bash
# Get all lists in JSON
uv run scripts/ms-todo-sync.py -j list

# Get pending tasks in JSON (includes task IDs)
uv run scripts/ms-todo-sync.py -j pending

# Add task and get JSON response
uv run scripts/ms-todo-sync.py -j add "test task"
```

---

### Authentication Commands

#### `login` — Login (single-step)

```bash
uv run scripts/ms-todo-sync.py login
```

**Note**: This is an interactive command requiring browser login. **Do NOT** use with `-j` or `-q` options.

**Output example:**
```
✓ Verification code generated

Please visit the following link to log in:
https://microsoft.com/devicelogin

Enter verification code: ABC123XYZ

Press Enter after you have completed login in the browser...
```

#### `logout` — Clear login info

```bash
uv run scripts/ms-todo-sync.py logout
```

Use only when user explicitly requests account switch or clearing login data.

---

### List Management

#### `list` / `ls` — List all task lists

```bash
uv run scripts/ms-todo-sync.py list
uv run scripts/ms-todo-sync.py ls  # alias
uv run scripts/ms-todo-sync.py -q list  # quiet mode, ID only
uv run scripts/ms-todo-sync.py -j list  # JSON format
uv run scripts/ms-todo-sync.py -v list  # detailed info
```

#### `list add` / `new-list` — Create new list

```bash
uv run scripts/ms-todo-sync.py list add "<name>"
uv run scripts/ms-todo-sync.py new-list "<name>"  # alias
```

#### `list remove` / `rm-list` — Delete list

```bash
uv run scripts/ms-todo-sync.py list remove "<name>" [-y]
uv run scripts/ms-todo-sync.py rm-list "<name>" [-y]  # alias
```

| Option | Description |
|--------|-------------|
| `-y, --yes` | Skip confirmation prompt |

---

### Task Views

#### `show` / `tasks` — Show tasks in a list

```bash
uv run scripts/ms-todo-sync.py show              # Show default list tasks (incomplete only by default)
uv run scripts/ms-todo-sync.py show "<list>"     # Show tasks in specific list
uv run scripts/ms-todo-sync.py tasks             # alias
uv run scripts/ms-todo-sync.py show -a           # Include completed tasks
uv run scripts/ms-todo-sync.py -j show           # JSON format
```

| Option | Description |
|--------|-------------|
| `-a, --all` | Include completed tasks |

---

### Task Operations

#### `add` / `new` — Add new task

```bash
uv run scripts/ms-todo-sync.py add "<title>" [options]
uv run scripts/ms-todo-sync.py new "<title>" [options]  # alias
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `title` | Yes | - | Task title (positional arg) |
| `-l, --list` | No | default list | Target list name |
| `-p, --priority` | No | `normal` | Priority: `low`, `normal`, `high` |
| `-d, --due` | No | - | Due date: days (`3`/`3d`) or date (`2026-02-15`) |
| `-r, --remind` | No | - | Reminder: `3h`/`2d`/`"2026-02-15 14:30"` |
| `--recur` | No | - | Recurrence: `daily`/`weekdays`/`weekly`/`monthly`, with interval: `daily:2` |
| `-n, --note` | No | - | Task note/description |
| `-t, --tags` | No | - | Comma-separated tags |

**Behavior**: List is auto-created if it doesn't exist.

**Error handling**: Command fails with exit code 1 on invalid date format.

#### `done` / `complete` — Mark task as completed

```bash
uv run scripts/ms-todo-sync.py done <ID or title> [-l "<list>"]
uv run scripts/ms-todo-sync.py complete <ID or title> [-l "<list>"]  # alias
```

| Option | Description |
|--------|-------------|
| `-l, --list` | List name (optional, searches all lists if omitted) |

**Smart detection**: Auto-detects input as ID or title. **Recommended**: Get ID first via `-q` or `-j`.

#### `remove` / `rm` — Delete task

```bash
uv run scripts/ms-todo-sync.py remove <ID or title> [-l "<list>"] [-y]
uv run scripts/ms-todo-sync.py rm <ID or title> [-l "<list>"] [-y]  # alias
```

| Option | Description |
|--------|-------------|
| `-l, --list` | List name (optional, searches all lists if omitted) |
| `-y, --yes` | Skip confirmation prompt |

**Smart detection**: Auto-detects input as ID or title. **Recommended**: Get ID first via `-q` or `-j`.

#### `view` / `info` — View task details

```bash
uv run scripts/ms-todo-sync.py view <ID or title> [-l "<list>"]
uv run scripts/ms-todo-sync.py info <ID or title> [-l "<list>"]  # alias
```

| Option | Description |
|--------|-------------|
| `-l, --list` | List name (optional, searches all lists if omitted) |

**Smart detection**: Auto-detects input as ID or title. **Recommended**: Get ID first via `-q` or `-j`.

---

### Search and Views

#### `find` / `search` — Search and filter tasks

```bash
uv run scripts/ms-todo-sync.py find "<keyword>"                    # Search tasks containing keyword
uv run scripts/ms-todo-sync.py find                                # List all tasks (no keyword = pure filter)
uv run scripts/ms-todo-sync.py find --incomplete                   # Show only incomplete tasks
uv run scripts/ms-todo-sync.py find --completed                    # Show only completed tasks
uv run scripts/ms-todo-sync.py find --created-after "2026-01-01"   # Filter by creation date
uv run scripts/ms-todo-sync.py find --created-before "2026-04-01"  # Filter by creation date
uv run scripts/ms-todo-sync.py find --due-after "2026-04-01"        # Filter by due date
uv run scripts/ms-todo-sync.py find --due-before "2026-04-15"      # Filter by due date
```

**Combined filter examples:**
```bash
# Incomplete tasks due this week
uv run scripts/ms-todo-sync.py find --due-after "2026-04-13" --due-before "2026-04-19" --incomplete

# Search and show incomplete only
uv run scripts/ms-todo-sync.py find "report" --incomplete

# Search tasks created in date range
uv run scripts/ms-todo-sync.py find "project" --created-after "2026-04-01"
```

| Option | Description |
|--------|-------------|
| `keyword` | Search keyword (optional, omit for pure filtering) |
| `--completed` | Show only completed tasks |
| `--incomplete` | Show only incomplete tasks |
| `--created-after` | Filter tasks created after date (YYYY-MM-DD) |
| `--created-before` | Filter tasks created before date (YYYY-MM-DD) |
| `--due-after` | Filter tasks due after date (YYYY-MM-DD) |
| `--due-before` | Filter tasks due before date (YYYY-MM-DD) |

**Note**: `--completed` and `--incomplete` cannot be used together - command will fail.

**JSON output includes applied filters:**
```json
{
  "success": true,
  "data": {
    "keyword": "report",
    "filters": {
      "completed": null,
      "incomplete": true,
      "createdAfter": null,
      "createdBefore": null,
      "dueAfter": "2026-04-01",
      "dueBefore": "2026-04-30"
    },
    "total": 5,
    "results": [...]
  }
}
```

#### `today` — Tasks due today

```bash
uv run scripts/ms-todo-sync.py today
uv run scripts/ms-todo-sync.py -j today  # JSON format
```

#### `overdue` — Overdue tasks

```bash
uv run scripts/ms-todo-sync.py overdue
uv run scripts/ms-todo-sync.py -j overdue  # JSON format
```

#### `pending` / `all` — All incomplete tasks

```bash
uv run scripts/ms-todo-sync.py pending
uv run scripts/ms-todo-sync.py pending -g  # Group by list
uv run scripts/ms-todo-sync.py all  # alias (supports -g too)
```

| Option | Description |
|--------|-------------|
| `-g, --group` | Group results by list |

#### `stats` — Task statistics

```bash
uv run scripts/ms-todo-sync.py stats
```

#### `export` — Export all tasks to JSON

```bash
uv run scripts/ms-todo-sync.py export [-o "<filename>"]
```

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | `todo_export.json` | Output file path |

---

## Quick Examples

```bash
# View all lists
uv run scripts/ms-todo-sync.py list

# Add task to specific list (list auto-created if needed)
uv run scripts/ms-todo-sync.py add "Report" -l "Work" -p high -d 3 -n "Q4 Finance"

# Add task to default list
uv run scripts/ms-todo-sync.py add "Buy milk"

# Add task with 2-hour reminder
uv run scripts/ms-todo-sync.py add "Call client" -r 2h

# Agent recommended: get ID first, then operate
uv run scripts/ms-todo-sync.py -q pending          # Get all pending task IDs
uv run scripts/ms-todo-sync.py -j pending          # Get JSON format (with details)
uv run scripts/ms-todo-sync.py done <id>           # Complete by ID
uv run scripts/ms-todo-sync.py remove <id> -y      # Delete by ID

# Search then view
uv run scripts/ms-todo-sync.py find "report"
uv run scripts/ms-todo-sync.py view "report"

# Views
uv run scripts/ms-todo-sync.py -v pending -g       # All pending, grouped, verbose
uv run scripts/ms-todo-sync.py -j today            # Today's tasks (JSON)
uv run scripts/ms-todo-sync.py export -o "backup.json"  # Full export
```

---

## v1 to v2 Migration Guide

| v1 Command | v2 Command |
|------------|------------|
| `lists` | `list` / `ls` |
| `create-list` | `list add` / `new-list` |
| `delete-list` | `list remove` / `rm-list` |
| `tasks <list>` | `show <list>` / `tasks <list>` |
| `add` | `add` / `new` |
| `complete` | `done` / `complete` |
| `delete` | `remove` / `rm` |
| `detail` | `view` / `info` |
| `search` | `find` / `search` |
| `pending` | `pending` / `all` |
| `--json` | `-j` / `--json` |
| `-D, --description` | `-n, --note` |
| `-r, --reminder` | `-r, --remind` |
| `-R, --recurrence` | `--recur` |

**New options:**
- `-q, --quiet` - Quiet mode, ID only output
