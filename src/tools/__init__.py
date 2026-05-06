"""Tool registry: schemas + dispatcher."""
from . import fs, search, shell, todos

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List entries in a directory (non-recursive).",
            "parameters": {
                "type": "object",
                "properties": {
                    "directory": {"type": "string", "description": "Directory to list. Defaults to '.'."}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 text file. Returns lines prefixed with line numbers (1-indexed).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "offset": {"type": "integer", "description": "Line offset to start from (0-indexed)."},
                    "limit": {"type": "integer", "description": "Max lines to return."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Overwrite a file with new content. Requires user confirmation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit",
            "description": (
                "Replace `old_string` with `new_string` in a file. By default `old_string` "
                "must occur exactly once; set `replace_all` to replace every occurrence. "
                "Prefer this over write_file for targeted changes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_string": {"type": "string"},
                    "new_string": {"type": "string"},
                    "replace_all": {"type": "boolean", "default": False},
                },
                "required": ["path", "old_string", "new_string"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_shell",
            "description": "Run a shell command. Requires user confirmation. Returns exit code, stdout, stderr.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 60)."},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search file contents with a regex. Returns 'path:line:text' rows (max 200).",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Python-flavor regex."},
                    "path": {"type": "string", "description": "Root path to search. Default '.'."},
                    "glob": {"type": "string", "description": "Glob filter, e.g. '**/*.py'."},
                    "ignore_case": {"type": "boolean", "default": False},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "glob",
            "description": "List files matching a glob pattern (e.g. '**/*.py').",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "description": "Root path. Default '.'."},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_write",
            "description": (
                "Replace the session todo list. Use to plan multi-step work and track progress. "
                "Each todo: {id?, content, status: pending|in_progress|completed}."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "content": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                            },
                            "required": ["content"],
                        },
                    }
                },
                "required": ["todos"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_read",
            "description": "Read the current session todo list.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def execute_tool(name: str, args: dict) -> str:
    if name == "list_files":
        return fs.list_files(args.get("directory", "."))
    if name == "read_file":
        return fs.read_file(args["path"], args.get("offset", 0), args.get("limit"))
    if name == "write_file":
        return fs.write_file(args["path"], args["content"])
    if name == "edit":
        return fs.edit(args["path"], args["old_string"], args["new_string"], args.get("replace_all", False))
    if name == "execute_shell":
        return shell.execute_shell(args["command"], args.get("timeout", 60))
    if name == "grep":
        return search.grep(
            args["pattern"], args.get("path", "."), args.get("glob"), args.get("ignore_case", False)
        )
    if name == "glob":
        return search.glob_files(args["pattern"], args.get("path", "."))
    if name == "todo_write":
        return todos.todo_write(args["todos"])
    if name == "todo_read":
        return todos.todo_read()
    return f"Error: unknown tool {name!r}"
