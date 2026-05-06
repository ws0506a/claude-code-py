# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python re-implementation of a Claude Code-style terminal AI assistant. Despite the name, it talks to the **OpenAI Chat Completions API** (default model `gpt-4.1-mini`), not Anthropic's. The OpenAI SDK is initialized with no explicit base URL, so it reads `OPENAI_API_KEY` (and optionally `OPENAI_BASE_URL`) from the environment / `.env`.

## Commands

```bash
pip install -e .            # editable install; registers the `claude-code` script
claude-code                 # start the REPL (default model gpt-4.1-mini)
claude-code --model <name>  # override model
python tests/test_basic.py  # run the basic tool smoke test (script-style, not pytest)
```

There is no linter, formatter, or pytest setup configured.

## Architecture

Three files under `src/` form a tight loop:

- **`src/main.py`** — Click CLI. Reads a line, calls `agent.chat()`, repeats. `exit`/`quit` ends the session. All output goes through `rich.Console`.
- **`src/agent.py`** — `ClaudeAgent` owns the message history. `chat()` runs an inner loop: send `messages + TOOL_DEFINITIONS` to `client.chat.completions.create(tool_choice="auto")`, append the assistant message, and if there are `tool_calls`, execute each via `execute_tool()`, append a `role: "tool"` result, then loop again. Loop exits only when the model returns a message with no tool calls. Tool results are truncated to 2000 chars before being appended to history.
- **`src/tools.py`** — Defines four tools: `list_files`, `read_file`, `write_file`, `execute_shell`. `TOOL_DEFINITIONS` is the OpenAI-format JSON schema list; `execute_tool(name, args)` dispatches to the Python implementations. `execute_shell` runs `subprocess.run(command, shell=True, ...)` with a 30s timeout and **no sandboxing** — any agent run can modify the filesystem and execute arbitrary commands in the cwd.

The package is imported as `src` (per `pyproject.toml` `packages = ["src"]` and the `src.main:main` entry point), so intra-package imports use relative form (`from .agent import ...`).

### Adding a tool

1. Implement the function in `src/tools.py` (return a string — results are passed back to the model as text).
2. Append a JSON-schema entry to `TOOL_DEFINITIONS`.
3. Add a branch in `execute_tool()`.

### Initial context injection

`ClaudeAgent.__init__` runs `os.listdir(".")` and appends the result as a second system message. The cwd at launch time is what the agent sees as "the project."

## Notes / gotchas

- `setup.py` declares the console script as `main:main` while `pyproject.toml` declares it as `src.main:main`. The pyproject form is the one that works after `pip install -e .`; treat `setup.py` as stale.
- The README claims Anthropic API support, but `agent.py` only ever calls the OpenAI SDK.
