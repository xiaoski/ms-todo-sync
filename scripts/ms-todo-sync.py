# -*- coding: utf-8 -*-
"""
Microsoft To Do API Access Script
Access To Do lists and tasks using Microsoft Graph API

New CLI Design (v2):
- uv run scripts/ms-todo-sync.py list/ls              - List all task lists
- uv run scripts/ms-todo-sync.py list add <name>      - Create new list
- uv run scripts/ms-todo-sync.py list remove <name>   - Delete list
- uv run scripts/ms-todo-sync.py show [<list>]        - Show tasks (default or specific list)
- uv run scripts/ms-todo-sync.py add <title>          - Add new task
- uv run scripts/ms-todo-sync.py done <id-or-title>   - Mark task as done
- uv run scripts/ms-todo-sync.py remove <id-or-title> - Delete task
- uv run scripts/ms-todo-sync.py view <id-or-title>   - View task details
- uv run scripts/ms-todo-sync.py find <keyword>       - Search tasks
- uv run scripts/ms-todo-sync.py today                - Show today's tasks
- uv run scripts/ms-todo-sync.py overdue              - Show overdue tasks
- uv run scripts/ms-todo-sync.py pending/all          - Show all pending tasks
- uv run scripts/ms-todo-sync.py stats                - Show statistics
- uv run scripts/ms-todo-sync.py export               - Export tasks
- uv run scripts/ms-todo-sync.py login                - Login
- uv run scripts/ms-todo-sync.py logout               - Logout
"""

# type: ignore  # Ignore missing type hints in msal library

import requests
import json
import os
import atexit
import argparse
import sys
import io
from typing import List, Dict, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
import msal  # type: ignore


# --- Set default encoding to UTF-8 ---
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
if sys.stdin.encoding != 'utf-8':
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
# ------------------------------------


# Constants
DEFAULT_CLIENT_ID = "82faeadf-5106-4aa0-bb0d-2c94b300e92a"
TOKEN_CACHE_FILE = "~/.mstodo_token_cache.json"
DEVICE_FLOW_CACHE_FILE = "~/.mstodo_device_flow.json"
PRIORITY_HIGH = "high"
PRIORITY_NORMAL = "normal"
PRIORITY_LOW = "low"
STATUS_NOT_STARTED = "notStarted"
STATUS_IN_PROGRESS = "inProgress"
STATUS_COMPLETED = "completed"


class MicrosoftTodoClient:
    """Microsoft To Do Client"""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        tenant_id: str = "common",
        cache_file: Optional[str] = None,
        debug: bool = False
    ):
        self.client_id = client_id or DEFAULT_CLIENT_ID
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.authority = f"https://login.microsoftonline.com/{tenant_id}"
        self.scopes = ["Tasks.Read", "Tasks.ReadWrite"]
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"
        self.access_token = None
        self.debug = debug

        if cache_file is None:
            cache_file = os.path.expanduser(TOKEN_CACHE_FILE)
        self.cache_file = cache_file

        self.cache = msal.SerializableTokenCache()
        if os.path.exists(self.cache_file):
            with open(self.cache_file, "r", encoding="utf-8") as f:
                self.cache.deserialize(f.read())

        atexit.register(self._save_cache)

    def _save_cache(self) -> None:
        if self.cache.has_state_changed:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                f.write(self.cache.serialize())

    def authenticate(self, force_refresh: bool = False) -> bool:
        app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
            token_cache=self.cache
        )

        if not force_refresh:
            accounts = app.get_accounts()
            if accounts:
                result = app.acquire_token_silent(self.scopes, account=accounts[0])
                if result and "access_token" in result:
                    self.access_token = result["access_token"]
                    return True

        return False

    def get_device_code_flow(self) -> Optional[Dict[str, Any]]:
        app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
            token_cache=self.cache
        )

        flow = app.initiate_device_flow(scopes=self.scopes)

        if "user_code" not in flow:
            error_msg = flow.get("error", "Unknown error")
            error_desc = flow.get("error_description", "No details")
            print("\n✗ Cannot create device code flow")
            print(f"Error: {error_msg}")
            print(f"Description: {error_desc}")
            return None

        flow_cache_file = os.path.expanduser(DEVICE_FLOW_CACHE_FILE)
        with open(flow_cache_file, "w", encoding="utf-8") as f:
            json.dump(flow, f)

        print("✓ Verification code generated")
        print("\nPlease visit the following link to log in:")
        print(f"{flow.get('verification_uri')}")
        print(f"\nEnter verification code: {flow.get('user_code')}")

        return flow

    def verify_device_code_flow(self) -> bool:
        flow_cache_file = os.path.expanduser(DEVICE_FLOW_CACHE_FILE)

        if not os.path.exists(flow_cache_file):
            print("✗ No flow information found to verify")
            print("Please run first: uv run scripts/ms-todo-sync.py login")
            return False

        try:
            with open(flow_cache_file, "r", encoding="utf-8") as f:
                flow = json.load(f)
        except Exception as e:
            print(f"✗ Failed to read flow information: {e}")
            return False

        app = msal.PublicClientApplication(
            self.client_id,
            authority=self.authority,
            token_cache=self.cache
        )

        result = app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            self.access_token = result["access_token"]
            self._save_cache()
            print("✓ Authentication successful! Login information saved.")
            os.remove(flow_cache_file)
            return True
        else:
            print(f"✗ Authentication failed: {result.get('error_description')}")
            return False

    def logout(self) -> None:
        self.access_token = None
        self.cache = msal.SerializableTokenCache()
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
            print("✓ Login information cleared")
        else:
            print("⚠️  No cached login information found")

    def is_authenticated(self) -> bool:
        return self.access_token is not None

    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not self.access_token:
            raise ValueError("Not authenticated, please call authenticate method first")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        url = f"{self.graph_endpoint}{endpoint}"

        if self.debug:
            self._print_debug_request(method, url, data)

        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        if self.debug:
            self._print_debug_response(response)

        if response.status_code >= 400:
            try:
                error_data = response.json()
                if self.debug:
                    print(f"  Error Body: {json.dumps(error_data, indent=2, ensure_ascii=False)}\n")
            except Exception:
                pass

        response.raise_for_status()

        if response.status_code == 204:
            if self.debug:
                print("  Body: (No Content)\n")
            return {}

        response_data = response.json()
        if self.debug:
            print("  Body: " + json.dumps(response_data, indent=2, ensure_ascii=False) + "\n")

        return response_data

    def _print_debug_request(self, method: str, url: str, data: Optional[Dict[str, Any]]) -> None:
        print("\n🔍 [DEBUG] API Request:")
        print(f"  Method: {method}")
        print(f"  URL: {url}")
        if data:
            print("  Request Body: " + json.dumps(data, indent=2, ensure_ascii=False))

    def _print_debug_response(self, response: requests.Response) -> None:
        print("\n🔍 [DEBUG] API Response:")
        print(f"  Status Code: {response.status_code}")
        print("  Headers: " + str(dict(response.headers)))

    def get_task_lists(self) -> List[Dict[str, Any]]:
        result = self._make_request("/me/todo/lists")
        return result.get("value", [])

    def create_task_list(self, display_name: str) -> Dict[str, Any]:
        data = {"displayName": display_name}
        return self._make_request("/me/todo/lists", method="POST", data=data)

    def delete_task_list(self, list_id: str) -> bool:
        self._make_request(f"/me/todo/lists/{list_id}", method="DELETE")
        return True

    def get_tasks(self, list_id: str) -> List[Dict[str, Any]]:
        result = self._make_request(f"/me/todo/lists/{list_id}/tasks")
        return result.get("value", [])

    def create_task(
        self,
        list_id: str,
        title: str,
        body: Optional[str] = None,
        due_date: Optional[str] = None,
        start_date: Optional[str] = None,
        reminder_date: Optional[str] = None,
        importance: str = PRIORITY_NORMAL,
        categories: Optional[List[str]] = None,
        recurrence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {"title": title, "importance": importance}

        if body:
            data["body"] = {"content": body, "contentType": "text"}
        if start_date:
            data["startDateTime"] = {"dateTime": start_date, "timeZone": "UTC"}
        if due_date:
            data["dueDateTime"] = {"dateTime": due_date, "timeZone": "UTC"}
        if reminder_date:
            data["reminderDateTime"] = {"dateTime": reminder_date, "timeZone": "UTC"}
        if categories:
            data["categories"] = categories
        if recurrence:
            data["recurrence"] = recurrence

        return self._make_request(f"/me/todo/lists/{list_id}/tasks", method="POST", data=data)

    def update_task(
        self,
        list_id: str,
        task_id: str,
        title: Optional[str] = None,
        body: Optional[str] = None,
        due_date: Optional[str] = None,
        reminder_date: Optional[str] = None,
        importance: Optional[str] = None,
        status: Optional[str] = None,
        categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {}

        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = {"content": body, "contentType": "text"}
        if due_date is not None:
            data["dueDateTime"] = {"dateTime": due_date, "timeZone": "UTC"}
        if reminder_date is not None:
            data["reminderDateTime"] = {"dateTime": reminder_date, "timeZone": "UTC"}
        if importance is not None:
            data["importance"] = importance
        if status is not None:
            data["status"] = status
        if categories is not None:
            data["categories"] = categories

        return self._make_request(f"/me/todo/lists/{list_id}/tasks/{task_id}", method="PATCH", data=data)

    def complete_task(self, list_id: str, task_id: str) -> Dict[str, Any]:
        return self.update_task(list_id, task_id, status=STATUS_COMPLETED)

    def delete_task(self, list_id: str, task_id: str) -> bool:
        self._make_request(f"/me/todo/lists/{list_id}/tasks/{task_id}", method="DELETE")
        return True

    def get_all_tasks(self) -> Dict[str, List[Dict[str, Any]]]:
        all_tasks = {}
        lists = self.get_task_lists()
        for task_list in lists:
            list_name = task_list.get("displayName")
            list_id = task_list.get("id")
            if list_id and list_name:
                tasks = self.get_tasks(list_id)
                all_tasks[list_name] = tasks
        return all_tasks

    def get_default_list(self) -> Optional[Dict[str, Any]]:
        lists = self.get_task_lists()
        for task_list in lists:
            if task_list.get("wellknownListName") == "defaultList":
                return task_list
        return lists[0] if lists else None

    def find_list_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        lists = self.get_task_lists()
        for task_list in lists:
            if task_list.get("displayName") == name:
                return task_list
        return None

    def get_task_by_id(self, list_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        try:
            return self._make_request(f"/me/todo/lists/{list_id}/tasks/{task_id}")
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                return None
            # Re-raise on 400 (invalid ID format) so caller can try title search
            if e.response is not None and e.response.status_code == 400:
                raise
            return None

    def find_task_by_title(self, list_id: str, title: str) -> Optional[Dict[str, Any]]:
        tasks = self.get_tasks(list_id)
        for task in tasks:
            if task.get("title") == title:
                return task
        return None

    def find_tasks_by_title(self, list_id: str, title: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        tasks = self.get_tasks(list_id)
        search_title = title if case_sensitive else title.lower()

        exact_matches = []
        partial_matches = []

        for task in tasks:
            task_title = task.get("title", "")
            if case_sensitive:
                if task_title == title:
                    exact_matches.append(task)
                elif search_title in task_title:
                    partial_matches.append(task)
            else:
                task_title_lower = task_title.lower()
                if task_title_lower == search_title:
                    exact_matches.append(task)
                elif search_title in task_title_lower:
                    partial_matches.append(task)

        return exact_matches + partial_matches

    def find_task_by_id_or_title(
        self,
        identifier: str,
        list_name: Optional[str] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Find task by ID (first) or title.
        Returns (task, list_name) tuple.
        On 400 (invalid ID format), falls back to title search.
        """
        # First, try to find by ID across all lists
        all_lists = self.get_task_lists()

        # If list is specified, search only that list
        if list_name:
            lst = self.find_list_by_name(list_name)
            if lst:
                # Try ID first (may raise 400 on invalid format)
                try:
                    task = self.get_task_by_id(lst["id"], identifier)
                    if task:
                        return task, list_name
                except requests.exceptions.HTTPError:
                    pass  # Fall through to title search
                # Then try title
                tasks = self.find_tasks_by_title(lst["id"], identifier)
                if tasks:
                    return tasks[0], list_name
            return None, None

        # Search all lists
        for lst in all_lists:
            try:
                task = self.get_task_by_id(lst["id"], identifier)
                if task:
                    return task, lst["displayName"]
            except requests.exceptions.HTTPError:
                pass  # Fall through to title search

        # If not found by ID, try by title
        for lst in all_lists:
            tasks = self.find_tasks_by_title(lst["id"], identifier)
            if tasks:
                return tasks[0], lst["displayName"]

        return None, None


# ==================== Helper Functions ====================

def _print_json_result(success: bool, data: Any = None, message: Optional[str] = None) -> None:
    result: Dict[str, Any] = {"success": success}
    result["data"] = data if data is not None else None
    if message:
        result["message"] = message
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _print_output(args, data: Any, human_formatter: Callable, json_data: Any = None) -> None:
    if getattr(args, "json", False):
        _print_json_result(True, json_data if json_data is not None else data)
    else:
        human_formatter()


def _print_success(args, message: str, data: Any = None) -> None:
    if getattr(args, "quiet", False):
        if data and isinstance(data, dict) and "id" in data:
            print(data["id"])
        return
    if getattr(args, "json", False):
        _print_json_result(True, data, message)
    else:
        print(f"✓ {message}")


def _print_error(args, message: str, exit_code: int = 1) -> None:
    if getattr(args, "json", False):
        _print_json_result(False, message=message)
        sys.exit(exit_code)
    else:
        print(f"❌ {message}")
        sys.exit(exit_code)


def _parse_recurrence(recurrence_str: str, start_date: datetime) -> Optional[Dict[str, Any]]:
    if not recurrence_str:
        return None

    parts = recurrence_str.lower().split(":")
    pattern_type = parts[0]
    interval = int(parts[1]) if len(parts) > 1 else 1

    recurrence = {
        "pattern": {"interval": interval},
        "range": {
            "type": "noEnd",
            "startDate": start_date.strftime("%Y-%m-%d")
        }
    }

    if pattern_type == "daily":
        recurrence["pattern"]["type"] = "daily"
    elif pattern_type == "weekdays":
        recurrence["pattern"]["type"] = "weekly"
        recurrence["pattern"]["daysOfWeek"] = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        recurrence["pattern"]["interval"] = 1
        recurrence["pattern"]["firstDayOfWeek"] = "sunday"
    elif pattern_type == "weekly":
        recurrence["pattern"]["type"] = "weekly"
        recurrence["pattern"]["daysOfWeek"] = [start_date.strftime("%A").lower()]
        recurrence["pattern"]["firstDayOfWeek"] = "sunday"
    elif pattern_type == "monthly":
        recurrence["pattern"]["type"] = "absoluteMonthly"
        recurrence["pattern"]["dayOfMonth"] = start_date.day
    else:
        print(f"❌ Invalid recurrence pattern: {pattern_type}")
        print("   Supported: daily, weekdays, weekly, monthly")
        return None

    return recurrence


def _error_list_not_found(list_name: str) -> None:
    print(f"❌ List not found: {list_name}")


def _error_task_not_found(task_name: str) -> None:
    print(f"❌ Task not found: {task_name}")


def _get_list_or_error(client: MicrosoftTodoClient, list_name: str) -> Optional[Dict[str, Any]]:
    task_list = client.find_list_by_name(list_name)
    if not task_list:
        _error_list_not_found(list_name)
    return task_list


def _get_target_list(
    client: MicrosoftTodoClient,
    list_name: Optional[str]
) -> Optional[Dict[str, Any]]:
    if list_name:
        return _get_list_or_error(client, list_name)
    task_list = client.get_default_list()
    if not task_list:
        print("❌ No task lists found")
    return task_list


def _parse_due_date(due_str: str) -> Optional[str]:
    try:
        if due_str.endswith("d"):
            days = int(due_str[:-1])
            due_datetime = datetime.now() + timedelta(days=days)
        elif due_str.isdigit():
            days = int(due_str)
            due_datetime = datetime.now() + timedelta(days=days)
        else:
            due_datetime = datetime.fromisoformat(due_str)
        return due_datetime.strftime("%Y-%m-%d") + "T00:00:00"
    except ValueError:
        print(f"❌ Invalid due date format: {due_str}")
        print("   Use YYYY-MM-DD, '2d' or just '3'")
        return None


def _parse_reminder(reminder_str: str) -> Optional[str]:
    try:
        if reminder_str.endswith("h"):
            hours = int(reminder_str[:-1])
            dt = datetime.now() + timedelta(hours=hours)
        elif reminder_str.endswith("d"):
            days = int(reminder_str[:-1])
            dt = datetime.now() + timedelta(days=days)
        else:
            try:
                dt = datetime.fromisoformat(reminder_str)
            except ValueError:
                try:
                    dt = datetime.strptime(reminder_str, "%Y-%m-%d %H:%M")
                except ValueError:
                    date_only = datetime.strptime(reminder_str, "%Y-%m-%d")
                    dt = date_only.replace(hour=9, minute=0, second=0)
        return dt.isoformat()
    except ValueError:
        print(f"❌ Invalid reminder format: {reminder_str}")
        print("   Supported: '3h', '2d', '2026-12-31 14:30', '2026-12-31'")
        return None


# ==================== Command Functions ====================

def cmd_list(args, client: MicrosoftTodoClient) -> None:
    """List all task lists"""
    if hasattr(args, "subcommand") and args.subcommand == "add":
        cmd_list_add(args, client)
    elif hasattr(args, "subcommand") and args.subcommand == "remove":
        cmd_list_remove(args, client)
    else:
        cmd_list_ls(args, client)


def cmd_list_ls(args, client: MicrosoftTodoClient) -> None:
    """List all task lists"""
    lists = client.get_task_lists()

    if args.json:
        json_data = []
        for lst in lists:
            item = {
                "id": lst["id"],
                "name": lst["displayName"],
                "isDefault": lst.get("wellknownListName") == "defaultList"
            }
            if args.verbose:
                item["createdDateTime"] = lst.get("createdDateTime")
            json_data.append(item)
        _print_json_result(True, {"total": len(json_data), "lists": json_data})
        return

    if args.quiet:
        for lst in lists:
            print(lst["id"])
        return

    if not lists:
        print("No task lists found")
        return

    print(f"\n📋 Task Lists ({len(lists)} total):\n")
    for i, lst in enumerate(lists, 1):
        print(f"{i}. {lst['displayName']}")
        if args.verbose:
            print(f"   ID: {lst['id']}")
            print(f"   Created: {lst.get('createdDateTime', 'N/A')}")


def cmd_list_add(args, client: MicrosoftTodoClient) -> None:
    """Create a new list"""
    task_list = client.create_task_list(args.name)

    if args.quiet:
        print(task_list["id"])
        return

    if args.json:
        _print_json_result(True, task_list, f"List created: {task_list['displayName']}")
    else:
        print(f"✓ List created: {task_list['displayName']}")
        if args.verbose:
            print(f"  ID: {task_list['id']}")


def cmd_list_remove(args, client: MicrosoftTodoClient) -> None:
    """Delete a list"""
    task_list = _get_list_or_error(client, args.name)
    if not task_list:
        if args.json:
            _print_json_result(False, message=f"List not found: {args.name}")
        return

    if not args.yes and not args.quiet and not args.json:
        confirm = input(f'Confirm delete list "{args.name}" and all its tasks? (y/n): ')
        if confirm.lower() != "y":
            print("Cancelled")
            return

    client.delete_task_list(task_list["id"])

    if args.json:
        _print_json_result(True, task_list, f"List deleted: {args.name}")
    elif not args.quiet:
        print(f"✓ List deleted: {args.name}")


def cmd_show(args, client: MicrosoftTodoClient) -> None:
    """Show tasks in a list (default or specific)"""
    if args.list:
        task_list = _get_list_or_error(client, args.list)
        if not task_list:
            return
    else:
        task_list = client.get_default_list()
        if not task_list:
            _print_error(args, "No task lists found")
            return

    tasks = client.get_tasks(task_list["id"])
    if not args.all:
        tasks = [t for t in tasks if t.get("status") != STATUS_COMPLETED]

    if args.json:
        json_data = []
        for task in tasks:
            item = {
                "id": task.get("id"),
                "title": task.get("title", "Untitled"),
                "status": task.get("status"),
                "importance": task.get("importance"),
                "dueDateTime": task.get("dueDateTime", {}).get("dateTime") if task.get("dueDateTime") else None
            }
            if args.verbose:
                item["body"] = task.get("body", {}).get("content")
                item["createdDateTime"] = task.get("createdDateTime")
                item["lastModifiedDateTime"] = task.get("lastModifiedDateTime")
            json_data.append(item)
        _print_json_result(True, {
            "list": task_list["displayName"],
            "includeCompleted": args.all,
            "total": len(json_data),
            "tasks": json_data
        })
        return

    if args.quiet:
        for task in tasks:
            print(task.get("id"))
        return

    if not tasks:
        print(f'\n📋 No tasks in list "{task_list["displayName"]}"')
        return

    print(f'\n📋 Tasks in list "{task_list["displayName"]}" ({len(tasks)} total):\n')
    for i, task in enumerate(tasks, 1):
        title = task.get("title", "Untitled")
        status = "[Completed]" if task.get("status") == STATUS_COMPLETED else "[In Progress]"
        priority = "⭐" if task.get("importance") == PRIORITY_HIGH else ""
        print(f"{i}. {status} {title} {priority}")
        if args.verbose:
            if task.get("body", {}).get("content"):
                print(f"   Notes: {task['body']['content'][:100]}")
            if task.get("dueDateTime"):
                print(f"   Due: {task['dueDateTime']['dateTime']}")


def cmd_add(args, client: MicrosoftTodoClient) -> None:
    """Add a new task"""
    if args.list:
        task_list = client.find_list_by_name(args.list)
        if not task_list:
            task_list = client.create_task_list(args.list)
            if not args.quiet and not args.json:
                print(f"✓ List created: {args.list}")
    else:
        task_list = client.get_default_list()
        if not task_list:
            _print_error(args, "No task lists found. Please create a list first.")
            return

    due_date = _parse_due_date(args.due) if args.due else None
    if args.due and due_date is None:
        if args.json:
            _print_json_result(False, message="Invalid due date format")
        sys.exit(1)

    reminder_date = _parse_reminder(args.remind) if args.remind else None
    if args.remind and reminder_date is None:
        if args.json:
            _print_json_result(False, message="Invalid reminder format")
        sys.exit(1)

    recurrence = None
    start_date = None
    if args.recur:
        if due_date:
            start_datetime = datetime.fromisoformat(due_date.replace("T00:00:00", ""))
        else:
            start_datetime = datetime.now()
            due_date = (start_datetime + timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")

        recurrence = _parse_recurrence(args.recur, start_datetime)
        if recurrence is None:
            if args.json:
                _print_json_result(False, message="Invalid recurrence pattern")
            sys.exit(1)
        start_date = start_datetime.strftime("%Y-%m-%dT09:00:00")

    task = client.create_task(
        list_id=task_list["id"],
        title=args.title,
        body=args.note,
        start_date=start_date,
        due_date=due_date,
        reminder_date=reminder_date,
        importance=args.priority,
        categories=args.tags.split(",") if args.tags else None,
        recurrence=recurrence,
    )

    if args.quiet:
        print(task["id"])
        return

    if args.json:
        _print_json_result(True, task, f"Task added: {task['title']}")
        return

    print(f"\n✓ Task added: {task['title']}")
    if recurrence:
        print("  🔄 Recurring task created")
    if args.verbose:
        print(f"  ID: {task['id']}")
        print(f"  Priority: {task['importance']}")


def cmd_done(args, client: MicrosoftTodoClient) -> None:
    """Mark task as completed"""
    task, list_name = client.find_task_by_id_or_title(args.identifier, args.list)

    if not task:
        _print_error(args, f"Task not found: {args.identifier}")
        return

    # Find the correct list for this task
    list_id = None
    if args.list and list_name:
        lst = client.find_list_by_name(list_name)
        if lst:
            list_id = lst["id"]
    else:
        all_lists = client.get_task_lists()
        for lst in all_lists:
            tasks = client.get_tasks(lst["id"])
            for t in tasks:
                if t.get("id") == task.get("id"):
                    list_id = lst["id"]
                    break
            if list_id:
                break

    if not list_id:
        _print_error(args, "Could not determine task list")
        return

    client.complete_task(list_id, task["id"])

    if args.quiet:
        print(task["id"])
        return

    if args.json:
        _print_json_result(True, task, f"Task completed: {args.identifier}")
    else:
        print(f"✓ Task completed: {args.identifier}")


def cmd_remove(args, client: MicrosoftTodoClient) -> None:
    """Delete a task"""
    task, list_name = client.find_task_by_id_or_title(args.identifier, args.list)

    if not task:
        _print_error(args, f"Task not found: {args.identifier}")
        return

    # Find the correct list for this task
    list_id = None
    if args.list and list_name:
        lst = client.find_list_by_name(list_name)
        if lst:
            list_id = lst["id"]
    else:
        all_lists = client.get_task_lists()
        for lst in all_lists:
            tasks = client.get_tasks(lst["id"])
            for t in tasks:
                if t.get("id") == task.get("id"):
                    list_id = lst["id"]
                    break
            if list_id:
                break

    if not list_id:
        _print_error(args, "Could not determine task list")
        return

    if not args.yes and not args.quiet and not args.json:
        confirm = input(f'Confirm delete task "{args.identifier}"? (y/n): ')
        if confirm.lower() != "y":
            print("Cancelled")
            return

    client.delete_task(list_id, task["id"])

    if args.quiet:
        print(task["id"])
        return

    if args.json:
        _print_json_result(True, task, f"Task deleted: {args.identifier}")
    else:
        print(f"✓ Task deleted: {args.identifier}")


def cmd_view(args, client: MicrosoftTodoClient) -> None:
    """View task details"""
    task, list_name = client.find_task_by_id_or_title(args.identifier, args.list)

    if not task:
        _print_error(args, f"Task not found: {args.identifier}")
        return

    if args.json:
        _print_json_result(True, task)
        return

    if args.quiet:
        print(task["id"])
        return

    print("\n" + "=" * 60)
    print("📌 Task Details")
    print("=" * 60 + "\n")
    print(f"📋 Title: {task.get('title', 'Untitled')}")
    status = "[Completed]" if task.get("status") == STATUS_COMPLETED else "[In Progress]"
    print(f"🔖 Status: {status}")
    print(f"🆔 ID: {task.get('id', 'N/A')}")
    print(f"📂 List: {list_name or 'Unknown'}")

    importance = task.get("importance", PRIORITY_NORMAL)
    importance_map = {PRIORITY_HIGH: "⭐ High", PRIORITY_NORMAL: "Normal", PRIORITY_LOW: "Low"}
    print(f"⚡ Priority: {importance_map.get(importance, importance)}")

    if task.get("dueDateTime"):
        due = task["dueDateTime"]["dateTime"].replace("T", " ")
        print(f"⏰ Due: {due}")

    if task.get("body", {}).get("content"):
        print(f"\n📝 Notes:\n{task['body']['content']}")

    print("\n" + "=" * 60 + "\n")


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse date string to datetime object"""
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None


def cmd_find(args, client: MicrosoftTodoClient) -> None:
    """Search for tasks"""
    # Validate conflicting status filters
    if args.completed and args.incomplete:
        _print_error(args, "Cannot specify both --completed and --incomplete")

    all_tasks = client.get_all_tasks()
    keyword = args.keyword.lower() if args.keyword else ""

    # Parse date filters with error handling
    date_filter_errors = []
    created_after = _parse_date(args.created_after) if args.created_after else None
    if args.created_after and created_after is None:
        date_filter_errors.append(f"Invalid --created-after format: {args.created_after}")

    created_before = _parse_date(args.created_before) if args.created_before else None
    if args.created_before and created_before is None:
        date_filter_errors.append(f"Invalid --created-before format: {args.created_before}")

    due_after = _parse_date(args.due_after) if args.due_after else None
    if args.due_after and due_after is None:
        date_filter_errors.append(f"Invalid --due-after format: {args.due_after}")

    due_before = _parse_date(args.due_before) if args.due_before else None
    if args.due_before and due_before is None:
        date_filter_errors.append(f"Invalid --due-before format: {args.due_before}")

    if date_filter_errors:
        for err in date_filter_errors:
            print(f"❌ {err}")
        sys.exit(1)

    results = []
    for list_name, tasks in all_tasks.items():
        for task in tasks:
            # Apply keyword filter (empty keyword matches all)
            if keyword:
                title = task.get("title", "").lower()
                body = task.get("body", {}).get("content", "").lower()
                if keyword not in title and keyword not in body:
                    continue

            # Apply status filter
            is_completed = task.get("status") == STATUS_COMPLETED
            if args.completed and not is_completed:
                continue
            if args.incomplete and is_completed:
                continue

            # Apply created date filters
            created_str = task.get("createdDateTime")
            if created_after or created_before:
                if not created_str:
                    continue  # Task has no createdDate, exclude it
                created_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                if created_after and created_date < created_after:
                    continue
                if created_before and created_date > created_before:
                    continue

            # Apply due date filters
            due_str = task.get("dueDateTime", {}).get("dateTime")
            if due_after or due_before:
                if not due_str:
                    continue  # Task has no due date, exclude it
                due_date = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
                if due_after and due_date < due_after:
                    continue
                if due_before and due_date > due_before:
                    continue

            results.append((list_name, task))

    if args.json:
        json_data = []
        for list_name, task in results:
            item = {
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "importance": task.get("importance"),
                "list": list_name,
                "dueDateTime": task.get("dueDateTime", {}).get("dateTime") if task.get("dueDateTime") else None,
                "createdDateTime": task.get("createdDateTime")
            }
            if args.verbose:
                item["body"] = task.get("body", {}).get("content")
            json_data.append(item)
        _print_json_result(True, {
            "keyword": args.keyword,
            "filters": {
                "completed": args.completed if args.completed else None,
                "incomplete": args.incomplete if args.incomplete else None,
                "createdAfter": args.created_after,
                "createdBefore": args.created_before,
                "dueAfter": args.due_after,
                "dueBefore": args.due_before
            },
            "total": len(json_data),
            "results": json_data
        })
        return

    if args.quiet:
        for list_name, task in results:
            print(task.get("id"))
        return

    if not results:
        keyword_desc = f'"{args.keyword}"' if args.keyword else ""
        print(f"\n🔍 No tasks found matching criteria {keyword_desc}")
        return

    keyword_desc = f' containing "{args.keyword}"' if args.keyword else ""
    print(f"\n🔍 Search results{keyword_desc} ({len(results)} found):\n")
    for list_name, task in results:
        status = "[Completed]" if task.get("status") == STATUS_COMPLETED else "[In Progress]"
        priority = "⭐" if task.get("importance") == PRIORITY_HIGH else ""
        print(f"{status} {task['title']} {priority}")
        print(f"   List: {list_name}")
        if args.verbose:
            created = task.get("createdDateTime", "N/A")
            due = task.get("dueDateTime", {}).get("dateTime", "N/A")
            print(f"   Created: {created}")
            print(f"   Due: {due}")
            if task.get("body", {}).get("content"):
                print(f"   Notes: {task['body']['content'][:100]}")


def cmd_today(args, client: MicrosoftTodoClient) -> None:
    """View tasks due today"""
    all_tasks = client.get_all_tasks()
    today = datetime.now().date()

    today_tasks = []
    for list_name, tasks in all_tasks.items():
        for task in tasks:
            if task.get("status") == STATUS_COMPLETED:
                continue
            due_date = task.get("dueDateTime", {}).get("dateTime")
            if due_date:
                task_date = datetime.fromisoformat(due_date.replace("Z", "+00:00")).date()
                if task_date == today:
                    today_tasks.append((list_name, task))

    if args.json:
        json_data = []
        for list_name, task in today_tasks:
            item = {
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "importance": task.get("importance"),
                "list": list_name,
                "dueDateTime": task.get("dueDateTime", {}).get("dateTime")
            }
            json_data.append(item)
        _print_json_result(True, {"total": len(json_data), "tasks": json_data})
        return

    if args.quiet:
        for list_name, task in today_tasks:
            print(task.get("id"))
        return

    if not today_tasks:
        print("\n📅 No tasks due today")
        return

    print(f"\n📅 Tasks due today ({len(today_tasks)} total):\n")
    for list_name, task in today_tasks:
        priority = "⭐" if task.get("importance") == PRIORITY_HIGH else ""
        print(f"[In Progress] {task['title']} {priority}")
        print(f"   List: {list_name}")


def cmd_overdue(args, client: MicrosoftTodoClient) -> None:
    """View overdue tasks"""
    all_tasks = client.get_all_tasks()
    now = datetime.now()

    overdue_tasks = []
    for list_name, tasks in all_tasks.items():
        for task in tasks:
            if task.get("status") == STATUS_COMPLETED:
                continue
            due_date = task.get("dueDateTime", {}).get("dateTime")
            if due_date:
                task_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                if task_date < now:
                    overdue_tasks.append((list_name, task, (now - task_date).days))

    overdue_tasks.sort(key=lambda x: x[2], reverse=True)

    if args.json:
        json_data = []
        for list_name, task, days in overdue_tasks:
            item = {
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "importance": task.get("importance"),
                "list": list_name,
                "dueDateTime": task.get("dueDateTime", {}).get("dateTime"),
                "overdueDays": days
            }
            json_data.append(item)
        _print_json_result(True, {"total": len(json_data), "tasks": json_data})
        return

    if args.quiet:
        for list_name, task, days in overdue_tasks:
            print(task.get("id"))
        return

    if not overdue_tasks:
        print("\n✓ No overdue tasks")
        return

    print(f"\n⚠️  Overdue tasks ({len(overdue_tasks)} total):\n")
    for list_name, task, days in overdue_tasks:
        priority = "⭐" if task.get("importance") == PRIORITY_HIGH else ""
        print(f"[In Progress] {task['title']} {priority}")
        print(f"   List: {list_name}")
        print(f"   Overdue: {days} days")


def cmd_pending(args, client: MicrosoftTodoClient) -> None:
    """Display incomplete tasks from all lists"""
    all_tasks = client.get_all_tasks()

    pending_tasks = []
    for list_name, tasks in all_tasks.items():
        for task in tasks:
            if task.get("status") != STATUS_COMPLETED:
                pending_tasks.append((list_name, task))

    if args.json:
        json_data = []
        for list_name, task in pending_tasks:
            item = {
                "id": task.get("id"),
                "title": task.get("title"),
                "status": task.get("status"),
                "importance": task.get("importance"),
                "list": list_name,
                "dueDateTime": task.get("dueDateTime", {}).get("dateTime") if task.get("dueDateTime") else None
            }
            json_data.append(item)
        _print_json_result(True, {"total": len(json_data), "tasks": json_data})
        return

    if args.quiet:
        for list_name, task in pending_tasks:
            print(task.get("id"))
        return

    if not pending_tasks:
        print("\n✓ No incomplete tasks")
        return

    if args.group:
        print(f"\n📋 All incomplete tasks ({len(pending_tasks)} total):\n")
        current_list = None
        for list_name, task in pending_tasks:
            if current_list != list_name:
                current_list = list_name
                print(f"\n📂 {list_name}:")
            priority = "⭐" if task.get("importance") == PRIORITY_HIGH else ""
            print(f"  [In Progress] {task['title']} {priority}")
    else:
        print(f"\n📋 All incomplete tasks ({len(pending_tasks)} total):\n")
        for list_name, task in pending_tasks:
            priority = "⭐" if task.get("importance") == PRIORITY_HIGH else ""
            print(f"[In Progress] {task['title']} {priority}")
            print(f"   List: {list_name}")


def cmd_stats(args, client: MicrosoftTodoClient) -> None:
    """Display statistics"""
    all_tasks = client.get_all_tasks()
    now = datetime.now()

    total_lists = len(all_tasks)
    total_tasks = 0
    completed = 0
    pending = 0
    high_priority = 0
    overdue_count = 0

    for tasks in all_tasks.values():
        for task in tasks:
            total_tasks += 1
            if task.get("status") == STATUS_COMPLETED:
                completed += 1
            else:
                pending += 1
                if task.get("importance") == PRIORITY_HIGH:
                    high_priority += 1
                due_date = task.get("dueDateTime", {}).get("dateTime")
                if due_date:
                    task_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                    if task_date < now:
                        overdue_count += 1

    if args.json:
        json_data = {
            "totalLists": total_lists,
            "totalTasks": total_tasks,
            "completed": completed,
            "pending": pending,
            "highPriority": high_priority,
            "overdue": overdue_count
        }
        if total_tasks > 0:
            json_data["completionRate"] = (completed / total_tasks) * 100  # type: ignore
        _print_json_result(True, json_data)
        return

    print("\n📊 Task Statistics:\n")
    print(f"  Total lists: {total_lists}")
    print(f"  Total tasks: {total_tasks}")
    print(f"  Completed: {completed}")
    print(f"  Pending: {pending}")
    print(f"  High priority: {high_priority}")
    print(f"  Overdue: {overdue_count}")

    if total_tasks > 0:
        completion_rate = (completed / total_tasks) * 100
        print(f"\n  Completion rate: {completion_rate:.1f}%")


def cmd_export(args, client: MicrosoftTodoClient) -> None:
    """Export tasks"""
    all_tasks = client.get_all_tasks()
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(all_tasks, f, ensure_ascii=False, indent=2)

    if args.json:
        _print_json_result(True, {"outputFile": args.output}, f"Tasks exported to: {args.output}")
    elif not args.quiet:
        print(f"✓ Tasks exported to: {args.output}")


def cmd_login(args, client: MicrosoftTodoClient) -> None:
    """Login - combines get and verify in one"""
    # First, try silent auth
    if client.authenticate():
        if args.json:
            _print_json_result(True, message="Already logged in")
        elif not args.quiet:
            print("✓ Already logged in")
        return

    # Get device code
    flow = client.get_device_code_flow()
    if not flow:
        if args.json:
            _print_json_result(False, message="Failed to get device code")
        sys.exit(1)

    # Wait for user to confirm (always wait, even in quiet/json mode for login)
    # In quiet mode, we still wait but don't show the interactive prompt
    if not args.quiet:
        input("\nPress Enter after you have completed login in the browser...")

    # Verify
    if client.verify_device_code_flow():
        if args.json:
            _print_json_result(True, message="Login successful")
        elif not args.quiet:
            print("✓ You can now start using ms-todo-sync.py")
        else:
            print("Login successful")
    else:
        if args.json:
            _print_json_result(False, message="Login failed")
        sys.exit(1)


def cmd_logout(args, client: MicrosoftTodoClient) -> None:
    """Logout and clear cached tokens"""
    client.logout()


# ==================== Argument Parser ====================

def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser"""
    parser = argparse.ArgumentParser(
        prog="ms-todo-sync.py",
        description="Microsoft To Do command line tool",
        epilog='Example: uv run scripts/ms-todo-sync.py add "Complete report" -l work -p high -d 3',
    )

    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet mode, only output IDs or errors")
    parser.add_argument("-j", "--json", action="store_true", help="Output in JSON format (machine-readable)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed information")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List management
    list_parser = subparsers.add_parser("list", help="List management")
    list_subparsers = list_parser.add_subparsers(dest="subcommand", help="List operations")
    list_subparsers.add_parser("ls", help="List all task lists")
    list_add_parser = list_subparsers.add_parser("add", help="Create new list")
    list_add_parser.add_argument("name", help="List name")
    list_remove_parser = list_subparsers.add_parser("remove", help="Delete list")
    list_remove_parser.add_argument("name", help="List name")
    list_remove_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # Aliases for list
    ls_parser = subparsers.add_parser("ls", help="List all task lists (alias for 'list')")
    ls_parser.set_defaults(command="list", subcommand=None)
    new_list_parser = subparsers.add_parser("new-list", help="Create new list (alias for 'list add')")
    new_list_parser.add_argument("name", help="List name")
    new_list_parser.set_defaults(command="list", subcommand="add")
    rm_list_parser = subparsers.add_parser("rm-list", help="Delete list (alias for 'list remove')")
    rm_list_parser.add_argument("name", help="List name")
    rm_list_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    rm_list_parser.set_defaults(command="list", subcommand="remove")

    # Show tasks
    show_parser = subparsers.add_parser("show", help="Show tasks (default or specific list)")
    show_parser.add_argument("list", nargs="?", help="List name (optional, uses default list)")
    show_parser.add_argument("-a", "--all", action="store_true", help="Include completed tasks")

    # Alias for show
    tasks_parser = subparsers.add_parser("tasks", help="Show tasks (alias for 'show')")
    tasks_parser.add_argument("list", nargs="?", help="List name (optional, uses default list)")
    tasks_parser.add_argument("-a", "--all", action="store_true", help="Include completed tasks")
    tasks_parser.set_defaults(command="show")

    # Add task
    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("title", help="Task title")
    add_parser.add_argument("-l", "--list", help="List name")
    add_parser.add_argument("-p", "--priority", choices=[PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH],
                            default=PRIORITY_NORMAL, help="Priority: low, normal, high")
    add_parser.add_argument("-d", "--due", help="Due date (3, 2d, YYYY-MM-DD)")
    add_parser.add_argument("-r", "--remind", help="Reminder (3h, 2d, YYYY-MM-DD HH:MM)")
    add_parser.add_argument("--recur", help="Recurrence (daily, weekdays, weekly, monthly)")
    add_parser.add_argument("-n", "--note", help="Task note/description")
    add_parser.add_argument("-t", "--tags", help="Tags (comma separated)")

    # Alias for add
    new_parser = subparsers.add_parser("new", help="Add a new task (alias for 'add')")
    new_parser.add_argument("title", help="Task title")
    new_parser.add_argument("-l", "--list", help="List name")
    new_parser.add_argument("-p", "--priority", choices=[PRIORITY_LOW, PRIORITY_NORMAL, PRIORITY_HIGH],
                            default=PRIORITY_NORMAL, help="Priority: low, normal, high")
    new_parser.add_argument("-d", "--due", help="Due date (3, 2d, YYYY-MM-DD)")
    new_parser.add_argument("-r", "--remind", help="Reminder (3h, 2d, YYYY-MM-DD HH:MM)")
    new_parser.add_argument("--recur", help="Recurrence (daily, weekdays, weekly, monthly)")
    new_parser.add_argument("-n", "--note", help="Task note/description")
    new_parser.add_argument("-t", "--tags", help="Tags (comma separated)")
    new_parser.set_defaults(command="add")

    # Done (complete) task
    done_parser = subparsers.add_parser("done", help="Mark task as completed")
    done_parser.add_argument("identifier", help="Task ID or title")
    done_parser.add_argument("-l", "--list", help="List name (optional)")

    # Alias for done
    complete_parser = subparsers.add_parser("complete", help="Mark task as completed (alias for 'done')")
    complete_parser.add_argument("identifier", help="Task ID or title")
    complete_parser.add_argument("-l", "--list", help="List name (optional)")
    complete_parser.set_defaults(command="done")

    # Remove task
    remove_parser = subparsers.add_parser("remove", help="Delete task")
    remove_parser.add_argument("identifier", help="Task ID or title")
    remove_parser.add_argument("-l", "--list", help="List name (optional)")
    remove_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")

    # Alias for remove
    rm_parser = subparsers.add_parser("rm", help="Delete task (alias for 'remove')")
    rm_parser.add_argument("identifier", help="Task ID or title")
    rm_parser.add_argument("-l", "--list", help="List name (optional)")
    rm_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    rm_parser.set_defaults(command="remove")

    # View task details
    view_parser = subparsers.add_parser("view", help="View task details")
    view_parser.add_argument("identifier", help="Task ID or title")
    view_parser.add_argument("-l", "--list", help="List name (optional)")

    # Alias for view
    info_parser = subparsers.add_parser("info", help="View task details (alias for 'view')")
    info_parser.add_argument("identifier", help="Task ID or title")
    info_parser.add_argument("-l", "--list", help="List name (optional)")
    info_parser.set_defaults(command="view")

    # Find/search tasks
    find_parser = subparsers.add_parser("find", help="Search for tasks")
    find_parser.add_argument("keyword", nargs="?", help="Search keyword (optional, allows pure filtering)")
    find_parser.add_argument("--created-after", help="Filter tasks created after date (YYYY-MM-DD)")
    find_parser.add_argument("--created-before", help="Filter tasks created before date (YYYY-MM-DD)")
    find_parser.add_argument("--due-after", help="Filter tasks due after date (YYYY-MM-DD)")
    find_parser.add_argument("--due-before", help="Filter tasks due before date (YYYY-MM-DD)")
    find_parser.add_argument("--completed", action="store_true", help="Show only completed tasks")
    find_parser.add_argument("--incomplete", action="store_true", help="Show only incomplete tasks")

    # Alias for find
    search_parser = subparsers.add_parser("search", help="Search for tasks (alias for 'find')")
    search_parser.add_argument("keyword", nargs="?", help="Search keyword (optional, allows pure filtering)")
    search_parser.add_argument("--created-after", help="Filter tasks created after date (YYYY-MM-DD)")
    search_parser.add_argument("--created-before", help="Filter tasks created before date (YYYY-MM-DD)")
    search_parser.add_argument("--due-after", help="Filter tasks due after date (YYYY-MM-DD)")
    search_parser.add_argument("--due-before", help="Filter tasks due before date (YYYY-MM-DD)")
    search_parser.add_argument("--completed", action="store_true", help="Show only completed tasks")
    search_parser.add_argument("--incomplete", action="store_true", help="Show only incomplete tasks")
    search_parser.set_defaults(command="find")

    # Quick views
    subparsers.add_parser("today", help="View tasks due today")
    subparsers.add_parser("overdue", help="View overdue tasks")

    pending_parser = subparsers.add_parser("pending", help="Show all incomplete tasks")
    pending_parser.add_argument("-g", "--group", action="store_true", help="Group by list")

    # Alias for pending
    all_parser = subparsers.add_parser("all", help="Show all incomplete tasks (alias for 'pending')")
    all_parser.add_argument("-g", "--group", action="store_true", help="Group by list")
    all_parser.set_defaults(command="pending")

    # Stats and export
    subparsers.add_parser("stats", help="Show statistics")

    export_parser = subparsers.add_parser("export", help="Export tasks to JSON")
    export_parser.add_argument("-o", "--output", default="todo_export.json", help="Output file")

    # Authentication
    subparsers.add_parser("login", help="Login to Microsoft To Do")
    subparsers.add_parser("logout", help="Logout and clear cache")

    return parser


def main() -> None:
    """Main function"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    client = MicrosoftTodoClient(debug=args.debug)

    # Logout command
    if args.command == "logout":
        cmd_logout(args, client)
        return

    # Login command
    if args.command == "login":
        try:
            cmd_login(args, client)
        except Exception as e:
            _print_error(args, str(e))
            if args.verbose:
                import traceback
                traceback.print_exc()
        return

    # Other commands require authentication
    if not client.authenticate():
        _print_error(args, "Not logged in. Please run: uv run scripts/ms-todo-sync.py login")

    # Command mapping
    commands: Dict[str, Callable] = {
        "list": cmd_list,
        "show": cmd_show,
        "add": cmd_add,
        "done": cmd_done,
        "remove": cmd_remove,
        "view": cmd_view,
        "find": cmd_find,
        "today": cmd_today,
        "overdue": cmd_overdue,
        "pending": cmd_pending,
        "stats": cmd_stats,
        "export": cmd_export,
    }

    if args.command in commands:
        try:
            commands[args.command](args, client)
        except Exception as e:
            _print_error(args, str(e))
            if args.verbose:
                import traceback
                traceback.print_exc()
    else:
        _print_error(args, f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
