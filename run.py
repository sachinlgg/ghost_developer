#!/usr/bin/env python3
"""
run.py — DevAgent Swarm with Live UI Streaming

Usage (Headless):
    python run.py --repo https://github.com/user/repo --task "Add dark mode" --reviewer user

Usage (Interactive):
    python run.py
"""
import os
import sys
import click
import threading
import webbrowser
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel

# Import isolated core execution
from core.swarm import execute_swarm_task

console = Console()
load_dotenv()

WORKSPACE = Path(__file__).parent / "workspace"

def _start_dashboard_server(state_file: Path):
    """Start the dashboard server in a background thread."""
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import ui.server as srv
        t = threading.Thread(
            target=srv.start, args=(state_file,), daemon=True
        )
        t.start()
        threading.Timer(1.0, lambda: webbrowser.open("http://localhost:8765")).start()
    except Exception as e:
        console.print(f"[yellow]⚠️ Could not start dashboard: {e}[/yellow]")

@click.command()
@click.option("--repo", "-r", help="GitHub repository URL")
@click.option("--task", "-t", help="Task description")
@click.option("--reviewer", "-R", help="GitHub username to assign reviewer")
def main(repo, task, reviewer):
    console.print(Panel.fit(
        "[bold cyan]🤖 DevAgent Swarm Interface[/bold cyan]\n"
        "[dim]Enter your task details below. Press Enter to submit.[/dim]",
        border_style="cyan"
    ))

    if not repo:
        repo = Prompt.ask("[bold blue]📦 GitHub Repository URL[/bold blue]")
    if not task:
        task = Prompt.ask("[bold yellow]🎯 What would you like the Swarm to build?[/bold yellow]")
    if reviewer is None:
        reviewer = Prompt.ask("[bold magenta]👤 Reviewer Username[/bold magenta] [dim](optional)[/dim]", default="")

    console.print("\n[bold green]🚀 Launching DevAgent Swarm...[/bold green]")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    gh_token = os.environ.get("GITHUB_TOKEN", "")

    if not api_key:
        console.print("[bold red]❌ Error:[/bold red] ANTHROPIC_API_KEY is not set in .env")
        sys.exit(1)
    if not gh_token:
        console.print("[bold red]❌ Error:[/bold red] GITHUB_TOKEN is not set in .env")
        sys.exit(1)

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # We extract the repo name just for the directory naming
    url = repo.rstrip("/")
    if url.endswith(".git"): url = url[:-4]
    repo_name = url.split("github.com/")[-1]
    
    run_dir = WORKSPACE / f"{repo_name.split('/')[-1]}_{run_id}"
    state_file = run_dir / "state.json"
    run_dir.mkdir(parents=True, exist_ok=True)
    
    # Start Web Dashboard UI before kicking off the engine
    _start_dashboard_server(state_file)
    
    # Fire up the isolated Omni-Agent Swarm execution loop
    execute_swarm_task(repo, task, reviewer, WORKSPACE, state_file)

if __name__ == "__main__":
    main()
