"""Tool-level tests. No network, no model calls."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src import confirm  # noqa: E402
from src.tools import execute_tool  # noqa: E402
from src.tools import todos  # noqa: E402


@pytest.fixture(autouse=True)
def _yolo_on():
    confirm.set_yolo(True)
    yield
    confirm.set_yolo(False)


@pytest.fixture(autouse=True)
def _reset_todos():
    todos._todos.clear()
    yield
    todos._todos.clear()


def test_write_then_read(tmp_path):
    f = tmp_path / "hello.txt"
    result = execute_tool("write_file", {"path": str(f), "content": "alpha\nbeta\n"})
    assert "Wrote" in result

    out = execute_tool("read_file", {"path": str(f)})
    assert "alpha" in out and "beta" in out
    assert out.startswith("1\t")  # line numbers


def test_edit_unique_replacement(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("x = 1\ny = 2\n", encoding="utf-8")
    result = execute_tool("edit", {"path": str(f), "old_string": "y = 2", "new_string": "y = 3"})
    assert "Edited" in result
    assert f.read_text(encoding="utf-8") == "x = 1\ny = 3\n"


def test_edit_rejects_ambiguous(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("x\nx\n", encoding="utf-8")
    result = execute_tool("edit", {"path": str(f), "old_string": "x", "new_string": "y"})
    assert "occurs 2 times" in result
    assert f.read_text(encoding="utf-8") == "x\nx\n"


def test_edit_replace_all(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("x\nx\n", encoding="utf-8")
    result = execute_tool(
        "edit", {"path": str(f), "old_string": "x", "new_string": "y", "replace_all": True}
    )
    assert "Edited" in result
    assert f.read_text(encoding="utf-8") == "y\ny\n"


def test_edit_missing_old_string(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("hello\n", encoding="utf-8")
    result = execute_tool("edit", {"path": str(f), "old_string": "nope", "new_string": "x"})
    assert "not found" in result


def test_grep(tmp_path):
    (tmp_path / "a.py").write_text("def foo():\n    pass\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("def bar():\n    pass\n", encoding="utf-8")
    result = execute_tool("grep", {"pattern": r"def \w+", "path": str(tmp_path)})
    assert "foo" in result and "bar" in result


def test_grep_with_glob(tmp_path):
    (tmp_path / "a.py").write_text("hit\n", encoding="utf-8")
    (tmp_path / "a.txt").write_text("hit\n", encoding="utf-8")
    result = execute_tool("grep", {"pattern": "hit", "path": str(tmp_path), "glob": "**/*.py"})
    assert "a.py" in result and "a.txt" not in result


def test_glob(tmp_path):
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "b.txt").write_text("", encoding="utf-8")
    result = execute_tool("glob", {"pattern": "**/*.py", "path": str(tmp_path)})
    assert "a.py" in result and "b.txt" not in result


def test_todo_roundtrip():
    written = execute_tool(
        "todo_write",
        {"todos": [
            {"content": "first", "status": "pending"},
            {"content": "second", "status": "in_progress"},
        ]},
    )
    assert "first" in written and "[~]" in written
    assert execute_tool("todo_read", {}) == written


def test_unknown_tool():
    assert "unknown tool" in execute_tool("does_not_exist", {})


# ---------- session persistence ----------
class _StubAgent:
    def __init__(self):
        self.model = "test-model"
        self.messages = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        self.usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "turns": 1}
        self._system_prefix_len = 1


def test_session_save_and_load(tmp_path, monkeypatch):
    from src import session as session_mod

    monkeypatch.setattr(session_mod, "SESSIONS_DIR", tmp_path)
    agent = _StubAgent()

    path = session_mod.new_session_path()
    session_mod.save(path, agent)
    assert path.is_file()

    fresh = _StubAgent()
    fresh.messages = []
    fresh.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "turns": 0}
    session_mod.load(path, fresh)

    assert len(fresh.messages) == 3
    assert fresh.usage["total_tokens"] == 15
    assert fresh.model == "test-model"
    assert fresh._system_prefix_len == 1


def test_session_resolve_by_index(tmp_path, monkeypatch):
    from src import session as session_mod
    import time

    monkeypatch.setattr(session_mod, "SESSIONS_DIR", tmp_path)
    agent = _StubAgent()

    p1 = session_mod.new_session_path()
    session_mod.save(p1, agent)
    time.sleep(0.05)
    # second path may collide on same timestamp; force a new name
    p2 = tmp_path / "later.json"
    session_mod.save(p2, agent)

    assert session_mod.latest_session() == p2
    assert session_mod.resolve("0") == p2
    assert session_mod.resolve("later") == p2
