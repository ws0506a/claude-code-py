"""Slash commands handled in the REPL (not sent to the model)."""
import os

from rich.console import Console
from rich.table import Table

from . import confirm

_console = Console()
_COMMANDS: dict[str, tuple] = {}


def _register(name: str, help_text: str):
    def deco(fn):
        _COMMANDS[name] = (fn, help_text)
        return fn
    return deco


@_register("/help", "Show available slash commands.")
def _cmd_help(args, agent):
    table = Table(show_header=True, header_style="bold")
    table.add_column("command", style="cyan", no_wrap=True)
    table.add_column("description")
    for name, (_, help_text) in sorted(_COMMANDS.items()):
        table.add_row(name, help_text)
    _console.print(table)


@_register("/model", "Show or change the model. Usage: /model [name]")
def _cmd_model(args, agent):
    if not args:
        _console.print(f"model: [cyan]{agent.model}[/cyan]")
        return
    agent.model = args[0]
    _console.print(f"model set to [cyan]{agent.model}[/cyan]")


@_register("/clear", "Clear conversation history (keeps system prompt + cwd context).")
def _cmd_clear(args, agent):
    agent.reset_messages()
    _console.print("[yellow]history cleared[/yellow]")


@_register("/cwd", "Show the current working directory.")
def _cmd_cwd(args, agent):
    _console.print(f"cwd: [cyan]{os.getcwd()}[/cyan]")


@_register("/cd", "Change working directory. Usage: /cd <path>")
def _cmd_cd(args, agent):
    if not args:
        _console.print("[red]Usage: /cd <path>[/red]")
        return
    path = os.path.expanduser(" ".join(args))
    try:
        os.chdir(path)
    except OSError as e:
        _console.print(f"[red]{e}[/red]")
        return
    agent.reset_messages()
    _console.print(f"cwd: [cyan]{os.getcwd()}[/cyan] [dim](history cleared)[/dim]")


@_register("/yolo", "Toggle confirmation skipping. Usage: /yolo [on|off]")
def _cmd_yolo(args, agent):
    if not args:
        confirm.set_yolo(not confirm._yolo)
    elif args[0].lower() in ("on", "true", "1"):
        confirm.set_yolo(True)
    elif args[0].lower() in ("off", "false", "0"):
        confirm.set_yolo(False)
    else:
        _console.print("[red]Usage: /yolo [on|off][/red]")
        return
    state = "on" if confirm._yolo else "off"
    color = "green" if confirm._yolo else "yellow"
    _console.print(f"yolo: [{color}]{state}[/{color}]")


@_register("/baseurl", "Show the OpenAI-compatible base URL in use.")
def _cmd_baseurl(args, agent):
    base = str(agent.client.base_url) if agent.client.base_url else "(default: api.openai.com)"
    _console.print(f"base_url: [cyan]{base}[/cyan]")


@_register("/history", "Show how many messages are in the conversation.")
def _cmd_history(args, agent):
    _console.print(f"messages: [cyan]{len(agent.messages)}[/cyan]")


@_register("/exit", "Exit the REPL.")
def _cmd_exit(args, agent):
    raise EOFError


def handle(line: str, agent) -> bool:
    """Try to handle a slash command. Returns True if `line` was a command."""
    if not line.startswith("/"):
        return False
    parts = line.strip().split()
    name = parts[0]
    args = parts[1:]
    entry = _COMMANDS.get(name)
    if not entry:
        _console.print(f"[red]Unknown command: {name}. Try /help[/red]")
        return True
    fn, _ = entry
    fn(args, agent)
    return True
