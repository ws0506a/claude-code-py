# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Terminal AI coding assistant in the spirit of Claude Code, written in Python. The CLI command is **`qingcode`**. The agent talks to any **OpenAI-compatible** endpoint via the `openai` SDK — set `OPENAI_BASE_URL` to point at DeepSeek, Qwen (DashScope), Moonshot/Kimi, vLLM, Ollama, etc. There is no Anthropic SDK in this codebase.

## Commands

```bash
pip install -e .            # editable install; registers the `qingcode` script
pip install -e ".[dev]"     # also installs pytest
qingcode                    # start the REPL (uses .env)
qingcode --model <name>     # override model for this session
qingcode --base-url <url>   # override OPENAI_BASE_URL
qingcode --yolo             # skip y/N confirmations on write/edit/shell
pytest                      # run tool tests (no model calls)
pytest tests/test_basic.py::test_edit_unique_replacement  # single test
```

`OPENAI_API_KEY` is required (loaded from `.env` via python-dotenv). `QINGCODE_MODEL` and `OPENAI_BASE_URL` are optional fallbacks for `--model` / `--base-url`.

## Architecture

The package is imported as `src` (per `pyproject.toml`), so intra-package imports use relative form (`from .tools import ...`).

- **`src/main.py`** — Click CLI. Loads `.env`, sets the global YOLO flag, instantiates `Agent`, runs the REPL. Ctrl-C cancels the current turn without quitting; Ctrl-D / `exit` / `quit` quits.
- **`src/agent.py`** — `Agent` owns the message history. `chat()` runs an inner loop: send `messages + TOOL_DEFINITIONS` with `tool_choice="auto"`, append the assistant message, dispatch each tool call via `execute_tool()`, append `role: "tool"` results, repeat until the model returns no `tool_calls`. Tool results are truncated to 4000 chars in history; a 400-char preview is rendered to the console.
- **`src/confirm.py`** — Module-level `_yolo` flag plus `confirm(action, detail)`. Returns True under `--yolo`, False on non-TTY stdin, otherwise prompts y/N. Imported by any tool that mutates state.
- **`src/tools/`** — Tool implementations + the OpenAI-format `TOOL_DEFINITIONS` list and the `execute_tool(name, args)` dispatcher (in `__init__.py`).
  - `fs.py` — `list_files`, `read_file` (with line numbers, optional `offset`/`limit`), `write_file` (confirm), `edit` (unique-string replace; rejects ambiguous matches unless `replace_all=True`; confirm).
  - `search.py` — `grep` (Python `re` over files, optional glob filter, max 200 hits) and `glob_files` (registered as `glob`). Both skip a default ignore set (`.git`, `__pycache__`, `node_modules`, `.venv`, etc.).
  - `shell.py` — `execute_shell` via `subprocess.run(shell=True, ...)`, 60 s default timeout, **no sandboxing** (confirm).
  - `todos.py` — Module-level `_todos: list[Todo]`. `todo_write` replaces the whole list; `todo_read` renders it. State is per-process — lost when `qingcode` exits.

### Adding a tool

1. Implement in the appropriate `src/tools/<area>.py`. Return a string — it is sent back to the model as the tool message content.
2. Append a JSON-schema entry to `TOOL_DEFINITIONS` in `src/tools/__init__.py`.
3. Add a branch in `execute_tool()` in the same file.
4. If the tool mutates state, call `confirm(action, detail)` first and bail out with a `"User declined ..."` string when it returns False.

### Initial context injection

`Agent.__init__` appends a second system message containing `os.getcwd()` and up to 30 sorted entries from the cwd. The cwd at launch determines what the agent sees as "the project" — running `qingcode` in the wrong directory is the most common confusion.

## Test conventions

`tests/test_basic.py` is pytest-based. Two autouse fixtures matter: `_yolo_on` flips confirmation off during tests, and `_reset_todos` clears the module-level todo list between tests. Tests use `tmp_path` and never hit the network or call a model.
