"""Filesystem tools: list_files, read_file, write_file, edit."""
import os
from ..confirm import confirm


def list_files(directory: str = ".") -> str:
    try:
        entries = sorted(os.listdir(directory))
        if not entries:
            return f"(empty directory: {directory})"
        return "\n".join(entries)
    except Exception as e:
        return f"Error: {e}"


def read_file(path: str, offset: int = 0, limit: int | None = None) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if offset:
            lines = lines[offset:]
        if limit is not None:
            lines = lines[:limit]
        numbered = [f"{i + 1 + offset}\t{line.rstrip(chr(10))}" for i, line in enumerate(lines)]
        return "\n".join(numbered) if numbered else "(empty file)"
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error: {e}"


def write_file(path: str, content: str) -> str:
    detail = f"path: {path}\nbytes: {len(content)}"
    if not confirm("write_file", detail):
        return "User declined to write the file."
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def edit(path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Replace `old_string` with `new_string` in `path`.

    If `replace_all` is False (default), `old_string` must occur exactly once.
    """
    if old_string == new_string:
        return "Error: old_string and new_string are identical."
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error: {e}"

    occurrences = content.count(old_string)
    if occurrences == 0:
        return f"Error: old_string not found in {path}."
    if occurrences > 1 and not replace_all:
        return (
            f"Error: old_string occurs {occurrences} times in {path}. "
            "Provide more context to make it unique, or set replace_all=true."
        )

    detail = f"path: {path}\nreplacements: {occurrences if replace_all else 1}"
    if not confirm("edit", detail):
        return "User declined the edit."

    new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as e:
        return f"Error: {e}"

    return f"Edited {path} ({occurrences if replace_all else 1} replacement(s))."
