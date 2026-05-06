"""Agent loop: send messages (streaming), dispatch tool calls, repeat."""
import json
import os
import time
from pathlib import Path

from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel

from .tools import TOOL_DEFINITIONS, execute_tool

_console = Console()

SYSTEM_PROMPT = """\
You are a terminal-based coding assistant inspired by Claude Code.

You have tools to read, search, write, edit files and run shell commands. Use them
to investigate the project before making changes — never guess at file contents.

Workflow guidance:
- Prefer `glob` / `grep` to locate code, then `read_file` to inspect it.
- Prefer `edit` over `write_file` for targeted changes; only use `write_file` for
  brand-new files or full rewrites.
- For multi-step tasks, call `todo_write` early to lay out the plan, then update
  it as you progress.
- `write_file`, `edit`, and `execute_shell` ask the user for confirmation. If a
  call returns "User declined ...", stop and ask the user what to do instead.
- When done, give a short summary of what changed (a sentence or two).
"""

# Compact when history grows past this many messages.
COMPACT_THRESHOLD = 40
# After compaction, keep at least this many recent messages.
KEEP_RECENT = 16
# Project-level docs the agent auto-loads (first match wins).
PROJECT_DOCS = ("CLAUDE.md", "AGENTS.md", ".claude.md")
# Errors that justify a retry with backoff.
_RETRIABLE = (APIConnectionError, APITimeoutError, RateLimitError, InternalServerError)


class Agent:
    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None):
        self.client = OpenAI(
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
        )
        self.model = model
        self.messages: list[dict] = []
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "turns": 0}
        self._system_prefix_len = 0
        self.reset_messages()

    # ---------- session setup ----------
    def reset_messages(self) -> None:
        """Reset history to system prompt + cwd snapshot + project doc (if any)."""
        try:
            cwd_listing = ", ".join(sorted(os.listdir("."))[:30])
        except OSError:
            cwd_listing = "(unavailable)"

        msgs: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"Working directory: {os.getcwd()}\nTop-level entries: {cwd_listing}",
            },
        ]
        doc = _load_project_doc()
        if doc:
            msgs.append({"role": "system", "content": doc})
            _console.print(f"[dim]loaded project context ({len(doc)} chars)[/dim]")

        self.messages = msgs
        self._system_prefix_len = len(msgs)

    # ---------- main loop ----------
    def chat(self, user_input: str) -> None:
        self.messages.append({"role": "user", "content": user_input})

        while True:
            self._maybe_compact()
            assistant_msg = self._stream_response()
            self.messages.append(assistant_msg)

            if not assistant_msg.get("tool_calls"):
                return

            for tc in assistant_msg["tool_calls"]:
                self._run_tool_call(tc)

    # ---------- streaming + retry ----------
    def _stream_response(self) -> dict:
        """Make one streaming completion call, render content live, accumulate
        tool calls, track usage. Returns an OpenAI-style assistant message dict."""
        stream = self._create_stream_with_retry()

        content_parts: list[str] = []
        tool_calls_acc: dict[int, dict] = {}
        usage = None

        try:
            with Live(
                Markdown(""),
                console=_console,
                refresh_per_second=12,
                vertical_overflow="visible",
            ) as live:
                for chunk in stream:
                    if getattr(chunk, "usage", None):
                        usage = chunk.usage
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta

                    if delta.content:
                        content_parts.append(delta.content)
                        live.update(Markdown("".join(content_parts)))

                    if delta.tool_calls:
                        for tcd in delta.tool_calls:
                            slot = tool_calls_acc.setdefault(
                                tcd.index,
                                {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                            )
                            if tcd.id:
                                slot["id"] = tcd.id
                            if tcd.function:
                                if tcd.function.name:
                                    slot["function"]["name"] += tcd.function.name
                                if tcd.function.arguments:
                                    slot["function"]["arguments"] += tcd.function.arguments
        finally:
            try:
                stream.close()
            except Exception:
                pass

        if usage:
            self.usage["prompt_tokens"] += usage.prompt_tokens or 0
            self.usage["completion_tokens"] += usage.completion_tokens or 0
            self.usage["total_tokens"] += usage.total_tokens or 0
        self.usage["turns"] += 1

        msg: dict = {"role": "assistant"}
        content = "".join(content_parts)
        if content:
            msg["content"] = content
        if tool_calls_acc:
            msg["tool_calls"] = [tool_calls_acc[i] for i in sorted(tool_calls_acc)]
        return msg

    def _create_stream_with_retry(self):
        backoff = 1.0
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    stream=True,
                    stream_options={"include_usage": True},
                )
            except _RETRIABLE as e:
                last_exc = e
                _console.print(
                    f"[yellow]{type(e).__name__}: {e} — retry {attempt + 1}/2 in {backoff:.0f}s[/yellow]"
                )
                time.sleep(backoff)
                backoff *= 2
            except TypeError:
                # Fallback for OpenAI-compatible servers that reject `stream_options`.
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    stream=True,
                )
        assert last_exc is not None
        raise last_exc

    # ---------- tool dispatch ----------
    def _run_tool_call(self, tool_call: dict) -> None:
        name = tool_call["function"]["name"]
        raw_args = tool_call["function"]["arguments"] or "{}"
        try:
            args = json.loads(raw_args)
        except json.JSONDecodeError as e:
            result = f"Error: invalid JSON arguments: {e}"
        else:
            _console.print(Panel(_render_args(args), title=f"[cyan]tool[/cyan] {name}", border_style="cyan"))
            try:
                result = execute_tool(name, args)
            except Exception as e:
                result = f"Error: tool raised {type(e).__name__}: {e}"

        if len(result) > 4000:
            result = result[:4000] + "\n... (truncated)"

        preview = result if len(result) <= 400 else result[:400] + "..."
        _console.print(Panel(preview, title=f"[green]result[/green] {name}", border_style="green"))

        self.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": name,
                "content": result,
            }
        )

    # ---------- compaction ----------
    def _maybe_compact(self) -> None:
        if len(self.messages) <= COMPACT_THRESHOLD:
            return
        head = self.messages[: self._system_prefix_len]
        # Walk forward from the boundary to land on a `user` message — slicing
        # in the middle of a tool_call/tool pair would break the API contract.
        boundary = max(self._system_prefix_len, len(self.messages) - KEEP_RECENT)
        while boundary < len(self.messages) and self.messages[boundary].get("role") != "user":
            boundary += 1
        if boundary >= len(self.messages):
            return
        tail = self.messages[boundary:]
        dropped = len(self.messages) - len(head) - len(tail)
        if dropped <= 0:
            return
        self.messages = head + [
            {"role": "system", "content": f"[{dropped} earlier messages omitted to save context.]"}
        ] + tail
        _console.print(f"[dim]auto-compacted: dropped {dropped} earlier messages[/dim]")


# ---------- helpers ----------
def _load_project_doc() -> str | None:
    for name in PROJECT_DOCS:
        p = Path(name)
        if not p.is_file():
            continue
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if len(content) > 8000:
            content = content[:8000] + "\n... (truncated)"
        return f"Project context loaded from {name}:\n\n{content}"
    return None


def _render_args(args: dict) -> str:
    if not args:
        return "(no args)"
    lines = []
    for k, v in args.items():
        rendered = json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v
        if len(rendered) > 200:
            rendered = rendered[:200] + "..."
        lines.append(f"[bold]{k}[/bold]: {rendered}")
    return "\n".join(lines)
