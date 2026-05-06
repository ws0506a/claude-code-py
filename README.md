# qingcode-py

A terminal AI coding assistant in the spirit of [Claude Code](https://claude.com/claude-code), written in Python. Talks to **any OpenAI-compatible API** — OpenAI, DeepSeek, Qwen (DashScope), Moonshot/Kimi, Together, local vLLM/Ollama, etc.

## Features

- **REPL workflow** — natural-language prompts in your terminal.
- **Tool-using agent** — the model can read, search, edit, and run things in your project until the task is done.
- **Confirmation by default** — destructive tools (`write_file`, `edit`, `execute_shell`) ask `y/N` before running. Pass `--yolo` to skip.
- **Provider-agnostic** — set `OPENAI_BASE_URL` to point at any OpenAI-compatible endpoint.

### Built-in tools

| tool | what it does |
| --- | --- |
| `list_files` | list a directory |
| `read_file` | read a file (with line numbers, optional offset/limit) |
| `write_file` | write a whole file (confirm) |
| `edit` | unique-string find-and-replace, no whole-file overwrite (confirm) |
| `grep` | regex search across files, with optional glob filter |
| `glob` | list files matching a glob pattern |
| `execute_shell` | run a shell command (confirm) |
| `todo_write` / `todo_read` | per-session task list the model uses to plan multi-step work |

## Install

```bash
git clone <this-repo>
cd qingcode-py
python -m venv .venv
# macOS/Linux:  source .venv/bin/activate
# Windows:      .venv\Scripts\activate
pip install -e .
```

## Configure

Copy `.env.example` to `.env` and fill in your key (and optionally a base URL / model):

```bash
cp .env.example .env
```

Examples:

```dotenv
# OpenAI
OPENAI_API_KEY=sk-...

# DeepSeek
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.deepseek.com/v1
QINGCODE_MODEL=deepseek-chat

# Qwen (DashScope)
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QINGCODE_MODEL=qwen-plus

# Local (Ollama / vLLM)
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
QINGCODE_MODEL=qwen2.5-coder:14b
```

## Run

```bash
qingcode                              # use .env defaults
qingcode --model deepseek-chat        # override model for this session
qingcode --base-url http://...        # override base URL
qingcode --yolo                       # skip y/N confirmations
```

Then talk to it:

```
>>> 看看 src/ 里有什么，找到 agent loop 然后给它加个超时
>>> 把 README 翻译成英文
>>> 跑一下测试
```

`exit` / `quit` / Ctrl-D leaves the session. Ctrl-C cancels the current turn without quitting.

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Project layout

```
src/
├── main.py          # CLI entry (click + rich)
├── agent.py         # message loop, tool dispatch
├── confirm.py       # y/N prompt used by destructive tools
└── tools/
    ├── __init__.py  # TOOL_DEFINITIONS + execute_tool dispatcher
    ├── fs.py        # list_files / read_file / write_file / edit
    ├── search.py    # grep / glob
    ├── shell.py     # execute_shell
    └── todos.py     # todo_write / todo_read
tests/
└── test_basic.py    # pytest covering the core tools
```

## License

MIT — see `LICENSE`.
