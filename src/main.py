"""CLI entry point."""
import os
import sys
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from .agent import Agent
from .confirm import set_yolo

_console = Console()


@click.command()
@click.option("--model", default=None, help="Model name. Falls back to $QINGCODE_MODEL or 'gpt-4.1-mini'.")
@click.option("--base-url", default=None, help="OpenAI-compatible base URL. Falls back to $OPENAI_BASE_URL.")
@click.option("--yolo", is_flag=True, help="Skip confirmation prompts for write/edit/shell tools.")
def main(model: str | None, base_url: str | None, yolo: bool) -> None:
    """A terminal AI coding assistant — works with any OpenAI-compatible API."""
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _console.print("[bold red]OPENAI_API_KEY not set.[/bold red] Put it in .env or export it.")
        sys.exit(1)

    model = model or os.getenv("QINGCODE_MODEL") or "gpt-4.1-mini"
    set_yolo(yolo)

    banner = (
        f"[bold blue]qingcode[/bold blue]\n"
        f"model: [cyan]{model}[/cyan]"
        + (f"  base_url: [cyan]{base_url or os.getenv('OPENAI_BASE_URL')}[/cyan]" if (base_url or os.getenv("OPENAI_BASE_URL")) else "")
        + ("\n[yellow]YOLO mode: confirmations disabled[/yellow]" if yolo else "")
        + "\nType 'exit' or Ctrl-D to quit. Ctrl-C cancels the current turn."
    )
    _console.print(Panel(banner, title="welcome"))

    agent = Agent(model=model, base_url=base_url, api_key=api_key)

    while True:
        try:
            user_input = _console.input("[bold green]>>> [/bold green]")
        except (EOFError, KeyboardInterrupt):
            _console.print()
            break

        if user_input.strip().lower() in {"exit", "quit"}:
            break
        if not user_input.strip():
            continue

        try:
            agent.chat(user_input)
        except KeyboardInterrupt:
            _console.print("\n[yellow]Turn cancelled.[/yellow]")
        except Exception as e:
            _console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    main()
