"""CLI entry point."""
import os
import sys
from pathlib import Path
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from . import session as session_mod
from .agent import Agent
from .commands import handle as handle_slash
from .confirm import set_yolo

_console = Console()


@click.command()
@click.option("--model", default=None, help="Model name. Falls back to $QINGCODE_MODEL or 'gpt-4.1-mini'.")
@click.option("--base-url", default=None, help="OpenAI-compatible base URL. Falls back to $OPENAI_BASE_URL.")
@click.option("--yolo", is_flag=True, help="Skip confirmation prompts for write/edit/shell tools.")
@click.option("--resume", is_flag=True, help="Resume the most recent saved session.")
@click.option("--resume-session", "resume_path", default=None, help="Resume a specific session file (path or stem).")
def main(model: str | None, base_url: str | None, yolo: bool, resume: bool, resume_path: str | None) -> None:
    """A terminal AI coding assistant — works with any OpenAI-compatible API."""
    # 1. cwd .env wins, AND overrides existing env vars — users editing .env
    #    expect it to take effect even if a stale OPENAI_API_KEY lives in their
    #    system environment.
    load_dotenv(override=True)
    # 2. fall back to .env next to the installed package (only fills holes left
    #    by step 1).
    package_env = Path(__file__).resolve().parent.parent / ".env"
    if package_env.is_file():
        load_dotenv(package_env, override=False)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        _console.print("[bold red]OPENAI_API_KEY not set.[/bold red] Put it in .env or export it.")
        sys.exit(1)

    model = model or os.getenv("QINGCODE_MODEL") or "gpt-4.1-mini"
    set_yolo(yolo)

    agent = Agent(model=model, base_url=base_url, api_key=api_key)

    # Resume: replace agent state from a saved session.
    resumed_from: Path | None = None
    if resume_path:
        target = Path(resume_path) if Path(resume_path).is_file() else session_mod.resolve(resume_path)
        if not target or not target.is_file():
            _console.print(f"[red]No session matching {resume_path!r}[/red]")
            sys.exit(1)
        meta = session_mod.load(target, agent)
        resumed_from = target
        _console.print(f"[green]resumed[/green] {target.name} ({meta.get('saved_at', '?')}, {len(agent.messages)} msgs)")
    elif resume:
        target = session_mod.latest_session()
        if not target:
            _console.print("[yellow]No saved sessions to resume; starting fresh.[/yellow]")
        else:
            meta = session_mod.load(target, agent)
            resumed_from = target
            _console.print(f"[green]resumed[/green] {target.name} ({meta.get('saved_at', '?')}, {len(agent.messages)} msgs)")

    # Each run gets its own session file (or continues the resumed one).
    session_path = resumed_from or session_mod.new_session_path()

    banner = (
        f"[bold blue]qingcode[/bold blue]\n"
        f"model: [cyan]{model}[/cyan]"
        + (f"  base_url: [cyan]{base_url or os.getenv('OPENAI_BASE_URL')}[/cyan]" if (base_url or os.getenv("OPENAI_BASE_URL")) else "")
        + ("\n[yellow]YOLO mode: confirmations disabled[/yellow]" if yolo else "")
        + f"\nsession: [dim]{session_path}[/dim]"
        + "\nType '/help' for commands. 'exit' or Ctrl-D to quit. Ctrl-C cancels the current turn."
    )
    _console.print(Panel(banner, title="welcome"))

    try:
        _repl(agent, session_path)
    finally:
        # Save on any exit (clean or via Ctrl-C/Ctrl-D), but only if there is
        # something beyond the initial system messages.
        if len(agent.messages) > agent._system_prefix_len:
            try:
                session_mod.save(session_path, agent)
                _console.print(f"[dim]session saved -> {session_path}[/dim]")
            except OSError as e:
                _console.print(f"[red]failed to save session: {e}[/red]")


def _repl(agent: Agent, session_path: Path) -> None:
    while True:
        try:
            user_input = _console.input("[bold green]>>> [/bold green]")
        except (EOFError, KeyboardInterrupt):
            _console.print()
            return

        stripped = user_input.strip()
        if stripped.lower() in {"exit", "quit"}:
            return
        if not stripped:
            continue
        if stripped.startswith("/"):
            try:
                if handle_slash(stripped, agent):
                    continue
            except EOFError:
                return
            except Exception as e:
                _console.print(f"[bold red]Command error:[/bold red] {e}")
                continue

        try:
            agent.chat(user_input)
        except KeyboardInterrupt:
            _console.print("\n[yellow]Turn cancelled.[/yellow]")
        except Exception as e:
            _console.print(f"[bold red]Error:[/bold red] {e}")


if __name__ == "__main__":
    main()
