"""Session persistence: save/restore conversation history to disk."""
import json
from datetime import datetime
from pathlib import Path

SESSIONS_DIR = Path.home() / ".qingcode" / "sessions"


def _ensure_dir() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def new_session_path() -> Path:
    _ensure_dir()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return SESSIONS_DIR / f"{stamp}.json"


def list_sessions(limit: int = 10) -> list[Path]:
    if not SESSIONS_DIR.is_dir():
        return []
    files = sorted(SESSIONS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[:limit]


def latest_session() -> Path | None:
    files = list_sessions(limit=1)
    return files[0] if files else None


def save(path: Path, agent) -> None:
    _ensure_dir()
    data = {
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "model": agent.model,
        "cwd": str(Path.cwd()),
        "messages": agent.messages,
        "usage": agent.usage,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load(path: Path, agent) -> dict:
    """Replace agent state from a session file. Returns the loaded metadata."""
    data = json.loads(path.read_text(encoding="utf-8"))
    agent.messages = data.get("messages", [])
    agent.usage = data.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "turns": 0})
    if data.get("model"):
        agent.model = data["model"]
    # Treat all loaded system messages as the prefix.
    prefix = 0
    for m in agent.messages:
        if m.get("role") == "system":
            prefix += 1
        else:
            break
    agent._system_prefix_len = prefix
    return data


def resolve(name_or_index: str) -> Path | None:
    """Find a session by either filename stem ('20260507-...') or index ('0' = newest)."""
    sessions = list_sessions(limit=50)
    if name_or_index.isdigit():
        idx = int(name_or_index)
        if 0 <= idx < len(sessions):
            return sessions[idx]
        return None
    for p in sessions:
        if p.stem == name_or_index or p.name == name_or_index:
            return p
    return None
