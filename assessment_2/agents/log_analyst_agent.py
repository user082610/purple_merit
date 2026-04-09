"""
Log Analyst Agent — runs after Triage.

Takes the structured hypotheses from Triage and hunts for evidence in the logs.
It doesn't just search for errors — it specifically tries to validate or
invalidate each hypothesis with log evidence.

Tools called: extract_stack_traces, extract_error_signatures,
              find_double_pickup_events, get_relevant_log_lines
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from shared.llm import get_llm
from shared.tracer import log_step, log_tool_call
from shared.console import console
from assessment_2.state import BugInvestigationState
from assessment_2.tools.log_tools import (
    extract_stack_traces,
    extract_error_signatures,
    find_double_pickup_events,
    get_relevant_log_lines,
)


SYSTEM_PROMPT = """You are a senior SRE analyzing logs to investigate a bug.

You've been given:
1. The triage team's hypotheses about what's causing the bug
2. Pre-processed log data (stack traces, error signatures, double-pickup events)

Your job:
1. For each hypothesis from triage, find log evidence that supports or refutes it
2. Identify the most significant error pattern — what's the smoking gun?
3. Note any anomalies in the logs that weren't in the triage hypotheses
4. Describe the failure sequence in plain English — what exactly happens step by step?

Output a JSON object:
{
  "hypothesis_evidence": [
    {
      "hypothesis": "copy from triage",
      "supported": true | false,
      "evidence": "specific log line or pattern that supports/refutes this"
    }
  ],
  "smoking_gun": "the single most important evidence line or pattern",
  "anomaly_pattern": "2-3 sentences describing what the logs reveal about the failure sequence",
  "noise_lines": ["log lines that look suspicious but are actually irrelevant — explain why"]
}

Be specific. Reference actual log content, timestamps, and worker IDs where possible.
No markdown outside the JSON."""


def run(state: BugInvestigationState) -> BugInvestigationState:
    console.print("[agent]▶ Log Analyst[/agent] — mining logs for evidence...")

    # Run all log tools
    stack_traces = extract_stack_traces(state["raw_logs"])
    error_sigs = extract_error_signatures(state["raw_logs"])
    double_pickups = find_double_pickup_events(state["raw_logs"])
    relevant_lines = get_relevant_log_lines(
        state["raw_logs"],
        keywords=["picked up", "IntegrityError", "duplicate", "WARNING", "swallowed", "processing"],
    )

    log_tool_call("assessment_2", "log_analyst", "extract_stack_traces", {}, {"count": len(stack_traces)})
    log_tool_call("assessment_2", "log_analyst", "extract_error_signatures", {}, {"count": len(error_sigs)})
    log_tool_call("assessment_2", "log_analyst", "find_double_pickup_events", {}, {"duplicates_found": len(double_pickups)})

    context = f"""
TRIAGE HYPOTHESES:
{json.dumps(state["hypotheses"], indent=2)}

STACK TRACES FOUND ({len(stack_traces)}):
{json.dumps(stack_traces, indent=2)}

ERROR SIGNATURES (frequency-sorted):
{json.dumps(error_sigs[:8], indent=2)}

DOUBLE PICKUP EVENTS (race condition evidence):
{json.dumps(double_pickups, indent=2)}

RELEVANT LOG LINES:
{json.dumps(relevant_lines[:20], indent=2)}
""".strip()

    llm = get_llm(temperature=0.2)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = llm.invoke(messages)

    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        result = json.loads(match.group()) if match else {}

    log_step(
        assessment="assessment_2",
        agent="log_analyst",
        step="analysis_complete",
        payload={
            "stack_traces_found": len(stack_traces),
            "double_pickups_found": len(double_pickups),
            "smoking_gun": result.get("smoking_gun", "")[:100],
        },
    )

    console.print(f"[info]  ✓ Log analysis done — {len(stack_traces)} stack traces, "
                  f"{len(double_pickups)} double-pickup events[/info]")

    return {
        **state,
        "stack_traces": stack_traces,
        "error_signatures": [s["signature"] for s in error_sigs[:5]],
        "log_evidence": relevant_lines[:15],
        "anomaly_pattern": result.get("anomaly_pattern", ""),
    }
