"""
core/config.py — Configuration loader for DevAgent Swarm.
Reads ANTHROPIC_API_KEY and GITHUB_TOKEN from .env file.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (where run.py lives)
_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env")


def get_anthropic_key() -> str:
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or not key.startswith("sk-ant"):
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is missing or invalid.\n"
            "  1. Copy .env.example → .env\n"
            "  2. Add your key from console.anthropic.com"
        )
    return key


def get_github_token() -> str:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise EnvironmentError(
            "GITHUB_TOKEN is missing.\n"
            "  1. Go to github.com/settings/tokens\n"
            "  2. Generate a token with 'repo' scope\n"
            "  3. Add it to your .env file"
        )
    return token


def get_claude_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")


def get_agent_timeout() -> int:
    return int(os.getenv("AGENT_TIMEOUT", "300"))


def is_verbose() -> bool:
    return os.getenv("VERBOSE", "false").lower() == "true"
