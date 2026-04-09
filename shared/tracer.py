"""
Lightweight tracer that records each agent's input/output to a JSONL file.
Nothing fancy — just enough so reviewers can follow the decision trail.
"""

import json
import os
from datetime import datetime
from pathlib import Path


TRACES_DIR = Path(__file__).parent.parent / "traces"


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def log_step(
    assessment: str,
    agent: str,
    step: str,
    payload: dict,
) -> None:
    """Append a single trace event to traces/<assessment>.jsonl"""
    _ensure_dir(TRACES_DIR)
    trace_file = TRACES_DIR / f"{assessment}.jsonl"

    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "agent": agent,
        "step": step,
        "data": payload,
    }

    with open(trace_file, "a") as f:
        f.write(json.dumps(record) + "\n")


def log_tool_call(assessment: str, agent: str, tool: str, args: dict, result: dict) -> None:
    log_step(
        assessment=assessment,
        agent=agent,
        step=f"tool_call:{tool}",
        payload={"args": args, "result": result},
    )
