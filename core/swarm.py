import os
import sys
import json
import time
import subprocess
import shutil
import re
from pathlib import Path
from datetime import datetime
from github import Github, Auth
from rich.console import Console

console = Console()

def get_repo_name(repo_url: str) -> str:
    url = repo_url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    return url.split("github.com/")[-1]

def git(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ Git command failed:[/bold red] git {' '.join(args)}")
        console.print(e.stderr)
        raise

def update_state(state_file: Path, **kwargs):
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except:
            pass
    state.update(kwargs)
    state_file.write_text(json.dumps(state, indent=2))

def parse_claude_stream(process, state_file: Path):
    logs = []

    def log_to_state(agent, msg):
        time_str = datetime.now().strftime("%H:%M:%S")
        logs.append({"time": time_str, "agent": agent, "msg": msg})
        update_state(state_file, log=logs)

    for line in iter(process.stdout.readline, ""):
        if not line:
            break
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        if data.get("type") == "assistant" and "message" in data:
            for item in data["message"].get("content", []):
                if item.get("type") == "text":
                    text = item.get("text", "").strip()
                    if text:
                        console.print(f"[dim]{text}[/dim]")
                        log_to_state("Omni-Agent", text[:100] + ("..." if len(text) > 100 else ""))
                
                elif item.get("type") == "tool_use":
                    tool = item.get("name")
                    tool_input = item.get("input", {})
                    detail = ""
                    if "command" in tool_input:
                        detail = f": {tool_input['command']}"
                    elif "path" in tool_input or "file paths" in tool_input:
                        path_str = tool_input.get("path") or tool_input.get("file paths")
                        detail = f": {path_str}"
                    elif "query" in tool_input:
                        detail = f": {tool_input['query']}"
                    
                    console.print(f"[bold magenta]🛠️  Using Tool: {tool}[/bold magenta][magenta]{detail}[/magenta]")
                    log_to_state("Omni-Agent", f"Executed tool: {tool}{detail}")

        elif data.get("type") == "result" and "result" in data:
            console.print(f"[bold green]✅ Agent cycle completed[/bold green]")
            log_to_state("Omni-Agent", "Finished cycle")

def execute_swarm_task(repo_url: str, task: str, reviewer: str, base_workspace: Path, state_file: Path = None):
    """
    Core swarm execution loop isolated from CLI parsing.
    Returns the PR URL or None if failed.
    """
    gh_token = os.environ.get("GITHUB_TOKEN", "")
    if not gh_token:
        console.print("[bold red]❌ Error:[/bold red] GITHUB_TOKEN is not set in .env")
        return None

    try:
        repo_name = get_repo_name(repo_url)
    except Exception:
        console.print(f"[bold red]❌ Invalid GitHub URL:[/bold red] {repo_url}")
        return None

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = base_workspace / f"{repo_name.split('/')[-1]}_{run_id}"
    repo_dir = run_dir / "repo"
    
    if not state_file:
        state_file = run_dir / "state.json"
    
    run_dir.mkdir(parents=True, exist_ok=True)
    update_state(state_file, task=task, repo_url=repo_url, reviewer=reviewer, status="running", started_at=datetime.utcnow().isoformat())

    # 1. Clone repository
    console.print(f"\n[cyan]📦 Cloning {repo_url}...[/cyan]")
    update_state(state_file, status="cloning", log=[{"time": datetime.now().strftime("%H:%M:%S"), "agent": "System", "msg": f"Cloning {repo_url}"}])
    
    clone_url = repo_url.replace("https://", f"https://{gh_token}@")
    try:
        subprocess.run(["git", "clone", clone_url, str(repo_dir)], check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]❌ Failed to clone repository.[/bold red]")
        return None
    
    # 2. Configure Claude Code CLI
    console.print("\n[magenta]🧠 Handing off to Omni-Agent...[/magenta]\n")
    update_state(state_file, status="running", log=[{"time": datetime.now().strftime("%H:%M:%S"), "agent": "Omni-Agent", "msg": "Started autonomous thought loop"}])
    
    prompt = f"You are an autonomous engineering agent inside the official Claude Code CLI.\nYour task is: {task}\nExplore, plan, code, test, and self-review. Be concise. Exit autonomously when completely finished."

    env = os.environ.copy()
    claude_bin = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    
    try:
        process = subprocess.Popen(
            [claude_bin, "--print", "--dangerously-skip-permissions", "--effort", "low", 
             "--model", os.environ.get("CLAUDE_MODEL", "haiku"), "--exclude-dynamic-system-prompt-sections",
             "--output-format", "stream-json", "--verbose", prompt],
            cwd=str(repo_dir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        parse_claude_stream(process, state_file)
        process.wait()
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Claude Code encountered an error: {e}[/bold red]")
        update_state(state_file, status="failed")
        return None

    # 3. Check for modifications
    console.print("\n[cyan]🔬 Checking changes...[/cyan]")
    status_str = git(["status", "--porcelain"], repo_dir)
    update_state(state_file, status="committing")
    
    if not status_str:
        console.print("[bold yellow]⚠️ No files were modified by Claude. Exiting.[/bold yellow]")
        update_state(state_file, status="done")
        return None

    # 4. Commit and Push
    console.print("[green]🚀 Committing to new branch...[/green]")
    safe_task = re.sub(r'[^a-zA-Z0-9]', '-', task.lower())[:30]
    branch_name = f"ai-feature/{safe_task}"
    git(["checkout", "-b", branch_name], repo_dir)
    git(["add", "-A"], repo_dir)
    git(["commit", "-m", f"feat: {task[:50]}"], repo_dir)
    git(["push", "-u", "origin", branch_name], repo_dir)

    # 5. Open PR
    console.print(f"[blue]🔀 Creating Pull Request...[/blue]")
    gh = Github(auth=Auth.Token(gh_token))
    github_repo = gh.get_repo(repo_name)
    try:
        pr = github_repo.create_pull(
            title=task[:70] + "..." if len(task) > 70 else task,
            body=f"Automated PR generated by DevAgent Swarm.\n\n**Task:** {task}",
            head=branch_name,
            base=github_repo.default_branch
        )
        if reviewer:
            try:
                pr.create_review_request(reviewers=[reviewer.strip()])
            except:
                pass
        
        console.print(f"\n[bold green]✅ Success! PR created:[/bold green] {pr.html_url}")
        update_state(state_file, status="done", pr_url=pr.html_url)
        return pr.html_url
    except Exception as e:
        console.print(f"\n[bold red]❌ Failed to create PR:[/bold red] {e}")
        update_state(state_file, status="failed")
        return None
