#!/usr/bin/env python3
"""
ghost_dev.py — The Autonomous GitHub Webhook Bot
Listens on port 8765 for GitHub JSON payloads. When an issue containing @DevAgent is caught,
it autonomously launches Omni-Agent in the background to resolve the issue.
"""
import os
import sys
import threading
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console

console = Console()
load_dotenv()

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    gh_token = os.environ.get("GITHUB_TOKEN", "")

    if not api_key or not gh_token:
        console.print("[bold red]❌ Error:[/bold red] API keys missing in .env")
        sys.exit(1)

    import ui.server as srv
    
    workspace = Path(__file__).parent / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    state_file = workspace / "webhook_state.json"
    
    # Initialize basic state
    if not state_file.exists():
        state_file.write_text("{}")
    
    console.print("[bold green]👻 Ghost Developer OS online.[/bold green]")
    console.print("   Listening for GitHub Webhooks on: [cyan]http://127.0.0.1:8765/webhook[/cyan]")
    console.print("\n[dim]To test this locally from GitHub, expose the port using ngrok:[/dim]")
    console.print("   [bold]ngrok http 8765[/bold]\n")
    
    try:
        # Run Webhook listener synchronously
        srv.start(state_file)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Shutting down Ghost Developer...[/bold yellow]")

if __name__ == "__main__":
    main()
