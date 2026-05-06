"""In-memory todo list shared across an agent session."""
from typing import Literal, TypedDict

Status = Literal["pending", "in_progress", "completed"]


class Todo(TypedDict):
    id: str
    content: str
    status: Status


_todos: list[Todo] = []
_VALID_STATUSES = {"pending", "in_progress", "completed"}


def todo_write(todos: list[dict]) -> str:
    """Replace the entire todo list with the provided one."""
    global _todos
    cleaned: list[Todo] = []
    for i, item in enumerate(todos):
        if not isinstance(item, dict):
            return f"Error: todo[{i}] is not an object."
        content = item.get("content")
        status = item.get("status", "pending")
        if not content or not isinstance(content, str):
            return f"Error: todo[{i}] missing 'content'."
        if status not in _VALID_STATUSES:
            return f"Error: todo[{i}] has invalid status {status!r}."
        cleaned.append({"id": str(item.get("id", i + 1)), "content": content, "status": status})
    _todos = cleaned
    return _render(_todos)


def todo_read() -> str:
    return _render(_todos) if _todos else "(no todos)"


def _render(todos: list[Todo]) -> str:
    icons = {"pending": "[ ]", "in_progress": "[~]", "completed": "[x]"}
    return "\n".join(f"{icons[t['status']]} {t['id']}. {t['content']}" for t in todos)
