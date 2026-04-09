"""Shared Rich console — one instance, consistent styling across both assessments."""

from rich.console import Console
from rich.theme import Theme

theme = Theme(
    {
        "agent": "bold cyan",
        "tool": "bold yellow",
        "decision.proceed": "bold green",
        "decision.pause": "bold yellow",
        "decision.rollback": "bold red",
        "info": "dim white",
        "header": "bold magenta",
    }
)

console = Console(theme=theme)
