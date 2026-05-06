"""Agent loop: send messages, dispatch tool calls, repeat."""
import json
import os
from openai import OpenAI
from rich.console import Console
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


class Agent:
    def __init__(self, model: str, base_url: str | None = None, api_key: str | None = None):
        self.client = OpenAI(
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
            api_key=api_key or os.getenv("OPENAI_API_KEY"),
        )
        self.model = model
        self.messages: list[dict] = []
        self.reset_messages()

    def reset_messages(self) -> None:
        """Reset history to just the system prompt + a fresh cwd snapshot."""
        try:
            cwd_listing = ", ".join(sorted(os.listdir("."))[:30])
        except OSError:
            cwd_listing = "(unavailable)"
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Working directory: {os.getcwd()}\nTop-level entries: {cwd_listing}"},
        ]

    def chat(self, user_input: str) -> None:
        self.messages.append({"role": "user", "content": user_input})

        while True:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
            )
            message = response.choices[0].message
            self.messages.append(message.model_dump(exclude_none=True))

            if message.content:
                _console.print(Markdown(message.content))

            if not message.tool_calls:
                return

            for tool_call in message.tool_calls:
                self._run_tool_call(tool_call)

    def _run_tool_call(self, tool_call) -> None:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments or "{}")
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
                "tool_call_id": tool_call.id,
                "name": name,
                "content": result,
            }
        )


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
