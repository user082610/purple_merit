"""
State model for the Assessment 1 war room orchestration.

Using TypedDict for LangGraph compatibility (it works better than Pydantic
models as graph state — LangGraph merges dicts at each node transition).
"""

from typing import Any, Literal, Optional
from typing_extensions import TypedDict


class WarRoomState(TypedDict, total=False):
    # Raw inputs loaded once at start
    metrics_summary: dict[str, Any]
    anomalies: list[dict]
    trend_summary: dict[str, Any]
    sentiment_summary: dict[str, Any]
    top_issues: list[str]
    sentiment_timeline: list[dict]
    release_notes: str

    # Agent outputs — each agent fills its section
    analyst_report: str
    pm_report: str
    marketing_report: str
    critic_report: str

    # Final coordinator output
    decision: Literal["PROCEED", "PAUSE", "ROLL_BACK"]
    rationale: str
    risk_register: list[dict]
    action_plan: list[dict]
    communication_plan: dict[str, str]
    confidence_score: float
    confidence_factors: list[str]

    # Bookkeeping
    iteration: int  # how many critic loops we've done
    errors: list[str]
