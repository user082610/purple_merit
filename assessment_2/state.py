"""
State model for the Assessment 2 bug investigation orchestration.
"""

from typing import Any, Optional
from typing_extensions import TypedDict


class BugInvestigationState(TypedDict, total=False):
    # Raw inputs
    bug_report: str
    raw_logs: str

    # Triage agent outputs
    symptoms: list[str]
    expected_behavior: str
    actual_behavior: str
    environment: dict[str, str]
    hypotheses: list[dict]          # [{hypothesis, confidence, rationale}]
    severity: str                   # Low / Medium / High / Critical

    # Log analyst outputs
    stack_traces: list[dict]        # [{worker, timestamp, error_type, trace_lines}]
    error_signatures: list[str]
    log_evidence: list[dict]        # [{timestamp, line, relevance}]
    anomaly_pattern: str            # plain-English description of what the logs show

    # Reproduction agent outputs
    repro_script_path: str          # path to the generated repro script
    repro_script_code: str          # contents of the repro script
    repro_run_output: str           # stdout/stderr from running the repro
    repro_succeeded: bool           # True if the repro actually failed as expected

    # Fix planner outputs
    root_cause: str
    root_cause_confidence: float
    patch_plan: list[dict]          # [{file, change_description, risk}]
    validation_plan: list[str]      # tests to add / checks to run
    open_questions: list[str]       # what we'd want to know before shipping fix

    # Critic outputs
    critic_feedback: str
    critic_approved: bool

    # Bookkeeping
    errors: list[str]
