"""Search tools: grep, glob."""
import re
from pathlib import Path

_DEFAULT_IGNORE = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
_MAX_HITS = 200


def _iter_files(root: Path, glob: str | None):
    pattern = glob or "**/*"
    for p in root.glob(pattern):
        if not p.is_file():
            continue
        if any(part in _DEFAULT_IGNORE for part in p.parts):
            continue
        yield p


def grep(pattern: str, path: str = ".", glob: str | None = None, ignore_case: bool = False) -> str:
    """Search file contents for a regex pattern. Returns matching `path:line:text` rows."""
    try:
        regex = re.compile(pattern, re.IGNORECASE if ignore_case else 0)
    except re.error as e:
        return f"Error: invalid regex: {e}"

    root = Path(path)
    if not root.exists():
        return f"Error: path not found: {path}"

    hits: list[str] = []
    for file in _iter_files(root, glob):
        try:
            with file.open("r", encoding="utf-8", errors="replace") as f:
                for lineno, line in enumerate(f, start=1):
                    if regex.search(line):
                        hits.append(f"{file}:{lineno}:{line.rstrip()}")
                        if len(hits) >= _MAX_HITS:
                            hits.append(f"... (truncated at {_MAX_HITS} matches)")
                            return "\n".join(hits)
        except (OSError, UnicodeDecodeError):
            continue

    return "\n".join(hits) if hits else "(no matches)"


def glob_files(pattern: str, path: str = ".") -> str:
    """List files matching a glob pattern (e.g. '**/*.py')."""
    root = Path(path)
    if not root.exists():
        return f"Error: path not found: {path}"
    matches = sorted(
        str(p)
        for p in root.glob(pattern)
        if p.is_file() and not any(part in _DEFAULT_IGNORE for part in p.parts)
    )
    return "\n".join(matches) if matches else "(no matches)"
