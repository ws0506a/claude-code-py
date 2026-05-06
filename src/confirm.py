"""User confirmation prompt for destructive tool calls."""
import sys
from rich.console import Console
from rich.panel import Panel

_console = Console()
_yolo = False


def set_yolo(enabled: bool) -> None:
    global _yolo
    _yolo = enabled


def confirm(action: str, detail: str) -> bool:
    """Ask the user y/n. Returns True if the action should proceed.

    In --yolo mode, always returns True.
    On a non-interactive stdin, defaults to False (deny).
    """
    if _yolo:
        return True
    if not sys.stdin.isatty():
        return False
    _console.print(Panel(detail, title=f"[yellow]Confirm:[/yellow] {action}", border_style="yellow"))
    answer = _console.input("[bold yellow]Proceed? [y/N] [/bold yellow]").strip().lower()
    return answer in ("y", "yes")
