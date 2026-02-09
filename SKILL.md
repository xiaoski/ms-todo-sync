---
name: ms-todo-sync
description: >
  A CLI skill to manage Microsoft To Do tasks via Microsoft Graph API.
  Supports listing, creating, completing, deleting, searching tasks and lists,
  viewing overdue/today/pending tasks, and exporting data.
metadata:
  version: 1.0.0
  author: xiaoski@qq.com
  license: MIT License
  tags: [productivity, task-management, microsoft-todo, cli]
  category: productivity
---

# ms-todo-sync

A Microsoft To Do command-line client for managing tasks and lists via Microsoft Graph API.

## Prerequisites

1. **Python >= 3.9** must be installed.
2. **uv** (Python package manager) must be installed. Install via `pip install uv` or see https://docs.astral.sh/uv/.
3. **Working directory**: All commands MUST be run from the root of this skill (the directory containing this SKILL.md file).
4. **Network access**: Requires internet access to Microsoft Graph API endpoints.
5. **Authentication**: First-time use requires interactive login via browser. See [Authentication Workflow](#authentication-workflow).

## Command Reference

All commands follow this pattern:

```
uv run scripts/ms-todo-sync.py [GLOBAL_OPTIONS] <command> [COMMAND_OPTIONS]
```

### Global Options

| Option | Description |
|--------|-------------|
| `-v, --verbose` | Show detailed information (IDs, dates, notes). **Must be placed BEFORE the subcommand.** |

> ⚠️ **Common mistake**: `-v` MUST come before the subcommand.
> - ✅ `uv run scripts/ms-todo-sync.py -v lists`
> - ❌ `uv run scripts/ms-todo-sync.py lists -v`

---

### Authentication

Authentication uses a two-step device code flow designed for non-interactive/agent environments.

#### `login get` — Get verification code

```bash
uv run scripts/ms-todo-sync.py login get
```

**Output example:**
```
✓ Verification code generated

Please visit the following link to log in:
https://microsoft.com/devicelogin

Enter verification code: ABC123XYZ

Verify with command: ms-todo-sync.py login verify
```

**Agent behavior**: Present the URL and verification code to the user. Wait for the user to confirm they have completed the browser login before proceeding.

#### `login verify` — Complete login

```bash
uv run scripts/ms-todo-sync.py login verify
```

**Output on success:**
```
✓ Authentication successful! Login information saved, you will be logged in automatically next time.
```

**Output on failure:**
```
✗ Authentication failed: <error description>
```

> ⚠️ **This command blocks** until Microsoft's server confirms the user completed browser authentication. Do NOT run this until the user confirms they have completed the browser step.

**Exit code**: 0 on success, 1 on failure.

#### `logout` — Clear saved login

```bash
uv run scripts/ms-todo-sync.py logout
```

Only use when the user explicitly asks to switch accounts or clear login data. Under normal circumstances, the token is cached and login is automatic.

---

### List Management

#### `lists` — List all task lists

```bash
uv run scripts/ms-todo-sync.py lists
uv run scripts/ms-todo-sync.py -v lists  # with IDs and dates
```

**Output example:**
```
📋 Task Lists (3 total):

1. Tasks
2. Work
3. Shopping
```

#### `create-list` — Create a new list

```bash
uv run scripts/ms-todo-sync.py create-list "<name>"
```

| Argument | Required | Description |
|----------|----------|-------------|
| `name` | Yes | Name of the new list |

Output: `✓ List created: <name>`

#### `delete-list` — Delete a list

```bash
uv run scripts/ms-todo-sync.py delete-list "<name>" [-y]
```

| Argument/Option | Required | Description |
|-----------------|----------|-------------|
| `name` | Yes | Name of the list to delete |
| `-y, --yes` | No | Skip confirmation prompt |

> ⚠️ **Agent must always use `-y`** to avoid blocking on interactive confirmation prompt.

Output: `✓ List deleted: <name>`

---

### Task Operations

#### `add` — Add a new task

```bash
uv run scripts/ms-todo-sync.py add "<title>" [options]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `title` | Yes | — | Task title (positional argument) |
| `-l, --list` | No | `"Tasks"` | Target list name |
| `-p, --priority` | No | `normal` | Priority: `low`, `normal`, `high` |
| `-d, --due` | No | — | Due date. Accepts an integer (days from now, e.g., `3`) or an ISO datetime string (e.g., `2026-02-15T09:00:00`) |
| `-D, --description` | No | — | Task description/notes |
| `-t, --tags` | No | — | Comma-separated tags (e.g., `"work,urgent"`) |
| `--create-list` | No | — | Automatically create the list if it doesn't exist |

**Output example:**
```
✓ Task added: Complete report
```

**Error if list not found (without `--create-list`):**
```
❌ List not found: NonExistent
💡 Use --create-list parameter to automatically create the list
```

#### `complete` — Mark a task as completed

```bash
uv run scripts/ms-todo-sync.py complete "<title>" [-l "<list>"]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `title` | Yes | — | Exact task title |
| `-l, --list` | No | `"Tasks"` | List name where the task resides |

Output: `✓ Task completed: <title>`

#### `delete` — Delete a task

```bash
uv run scripts/ms-todo-sync.py delete "<title>" [-l "<list>"] [-y]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `title` | Yes | — | Exact task title |
| `-l, --list` | No | `"Tasks"` | List name |
| `-y, --yes` | No | — | Skip confirmation prompt |

> ⚠️ **Agent must always use `-y`** to avoid blocking on interactive confirmation prompt.

Output: `✓ Task deleted: <title>`

---

### Task Views

#### `tasks` — List tasks in a specific list

```bash
uv run scripts/ms-todo-sync.py tasks "<list>" [-a]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `list` | Yes | — | List name (positional argument) |
| `-a, --all` | No | — | Include completed tasks (default: only incomplete) |

**Output example:**
```
📋 Tasks in list "Work" (2 total):

1. [In Progress] Write documentation ⭐
2. [In Progress] Review PR
```

#### `pending` — All incomplete tasks across all lists

```bash
uv run scripts/ms-todo-sync.py pending [-g]
```

| Option | Required | Description |
|--------|----------|-------------|
| `-g, --group` | No | Group results by list |

**Output example (with `-g`):**
```
📋 All incomplete tasks (3 total):

📂 Work:
  [In Progress] Write documentation ⭐
  [In Progress] Review PR

📂 Shopping:
  [In Progress] Buy groceries
```

#### `today` — Tasks due today

```bash
uv run scripts/ms-todo-sync.py today
```

Lists incomplete tasks with due date matching today. Output: `📅 No tasks due today` if none found.

#### `overdue` — Overdue tasks

```bash
uv run scripts/ms-todo-sync.py overdue
```

**Output example:**
```
⚠️  Overdue tasks (1 total):

[In Progress] Submit report ⭐
   List: Work
   Overdue: 3 days
```

#### `detail` — View full task details

```bash
uv run scripts/ms-todo-sync.py detail "<title>" [-l "<list>"]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `title` | Yes | — | Task title (supports **partial/fuzzy match**) |
| `-l, --list` | No | `"Tasks"` | List name |

When multiple tasks match, returns the most recently modified **incomplete** task. If all matches are completed, returns the most recently modified completed task.

#### `search` — Search tasks by keyword

```bash
uv run scripts/ms-todo-sync.py search "<keyword>"
```

Searches across all lists in both task titles and notes (case-insensitive).

**Output example:**
```
🔍 Search results (1 found):

[In Progress] Write documentation ⭐
   List: Work
```

#### `stats` — Task statistics

```bash
uv run scripts/ms-todo-sync.py stats
```

**Output example:**
```
📊 Task Statistics:

  Total lists: 3
  Total tasks: 15
  Completed: 10
  Pending: 5
  High priority: 2
  Overdue: 1

  Completion rate: 66.7%
```

#### `export` — Export all tasks to JSON

```bash
uv run scripts/ms-todo-sync.py export [-o "<filename>"]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `-o, --output` | No | `todo_export.json` | Output file path |

Output: `✓ Tasks exported to: <filename>`

---

## Error Handling

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Failure (not logged in, API error, invalid arguments, etc.) |

### Common Error Messages

| Error | Cause | Resolution |
|-------|-------|------------|
| `❌ Not logged in` | No cached token or token expired | Run `login get` then `login verify` |
| `❌ List not found: <name>` | Specified list does not exist | Check list name with `lists` command |
| `❌ Task not found: <name>` | No task with exact matching title | Check task title with `tasks` or `search` |
| `❌ Error: <message>` | API or network error | Retry; check network; use `-v` for stack trace |

---

## Agent Usage Guidelines

### Critical Rules

1. **Working directory**: Always `cd` to the directory containing this SKILL.md before running commands.
2. **Use `-y` for destructive commands**: Always pass `-y` to `delete` and `delete-list` to prevent blocking on interactive prompts.
3. **Global option placement**: `-v` must come BEFORE the subcommand, not after.
4. **Do not retry `login verify` automatically**: This command blocks waiting for user browser interaction. Only call it after the user confirms completion.
5. **Check login status first**: Before performing any task operations, run a lightweight command (e.g., `lists`) to verify authentication. Handle the "Not logged in" error gracefully.

### Recommended Workflow for Agents

```
1. cd <skill_directory>
2. uv run scripts/ms-todo-sync.py lists          # Test auth
   → If fails with exit code 1 ("Not logged in"):
     a. uv run scripts/ms-todo-sync.py login get  # Get code
     b. Present URL + code to user
     c. Wait for user confirmation
     d. uv run scripts/ms-todo-sync.py login verify
3. Perform requested task operations
4. Verify results (e.g., list tasks after adding)
```

### Task Title Matching

- `complete` and `delete` require **exact title match**.
- `detail` and `search` support **partial/fuzzy keyword match** (case-insensitive).
- When in doubt, use `search` first to find the exact title, then use it in subsequent commands.

---

## Quick Examples

```bash
# Add task with priority, due date, description, auto-create list
uv run scripts/ms-todo-sync.py add "Report" -l "Work" -p high -d 3 -D "Q4 financials" --create-list

# Search then complete (use exact title from search results)
uv run scripts/ms-todo-sync.py search "report"
uv run scripts/ms-todo-sync.py complete "Report" -l "Work"

# Delete (always use -y for agent)
uv run scripts/ms-todo-sync.py delete "Old task" -y

# Views
uv run scripts/ms-todo-sync.py -v pending -g          # all pending, grouped
uv run scripts/ms-todo-sync.py -v detail "report"      # task detail with fuzzy match
uv run scripts/ms-todo-sync.py export -o "backup.json"  # export all
```




