"""
Fix Planner Agent — proposes root cause and patch approach.

Has the full picture: triage hypotheses, log evidence, repro results.
Produces a root cause statement with confidence, a concrete patch plan,
and a validation checklist.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from shared.llm import get_llm
from shared.tracer import log_step
from shared.console import console
from assessment_2.state import BugInvestigationState


SYSTEM_PROMPT = """You are a senior engineer writing a fix plan for a confirmed bug.

You have the full investigation picture: the original bug report, log evidence,
and a reproduction result. Your job is to propose a root cause and a concrete patch plan.

Output a JSON object with this schema:
{
  "root_cause": "precise technical statement of what is actually broken",
  "root_cause_confidence": 0.0 to 1.0,
  "root_cause_evidence": ["list of specific evidence items that support this root cause"],
  "patch_plan": [
    {
      "file": "filename or module",
      "change": "specific code change description — be concrete, not vague",
      "why": "why this change fixes the root cause",
      "risk": "Low | Medium | High",
      "risk_note": "what could go wrong with this change"
    }
  ],
  "validation_plan": [
    "specific test or check to add/run to verify the fix"
  ],
  "open_questions": [
    "questions we'd want answered before shipping this fix to production"
  ]
}

Be specific about the fix. Don't say 'use a lock' — say 'wrap the LPOP + status UPDATE
in a Redis MULTI/EXEC transaction to make dequeue atomic'. Reference actual code patterns.
Return only JSON."""


def run(state: BugInvestigationState) -> BugInvestigationState:
    console.print("[agent]▶ Fix Planner[/agent] — proposing root cause and patch plan...")

    # Build a concise evidence bundle from all prior agents
    evidence_bundle = {
        "triage": {
            "top_hypothesis": state["hypotheses"][0] if state["hypotheses"] else {},
            "severity": state.get("severity"),
            "actual_behavior": state.get("actual_behavior"),
        },
        "log_analysis": {
            "anomaly_pattern": state.get("anomaly_pattern"),
            "double_pickup_count": len([
                e for e in state.get("log_evidence", [])
                if "IntegrityError" in e.get("content", "")
            ]),
            "top_error_signatures": state.get("error_signatures", [])[:3],
        },
        "reproduction": {
            "confirmed": state.get("repro_succeeded"),
            "script_path": state.get("repro_script_path"),
            "output_summary": state.get("repro_run_output", "")[:500],
        },
    }

    context = f"""
BUG REPORT SUMMARY:
{state['bug_report'][:600]}

EVIDENCE BUNDLE:
{json.dumps(evidence_bundle, indent=2)}

SAMPLE LOG EVIDENCE (most relevant lines):
{json.dumps(state.get('log_evidence', [])[:8], indent=2)}
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
        agent="fix_planner",
        step="plan_complete",
        payload={
            "root_cause_confidence": result.get("root_cause_confidence"),
            "patch_items": len(result.get("patch_plan", [])),
        },
    )

    confidence = result.get("root_cause_confidence", 0)
    console.print(
        f"[info]  ✓ Fix plan ready — confidence: {confidence:.0%}, "
        f"{len(result.get('patch_plan', []))} patch items[/info]"
    )

    return {
        **state,
        "root_cause": result.get("root_cause", ""),
        "root_cause_confidence": result.get("root_cause_confidence", 0.0),
        "patch_plan": result.get("patch_plan", []),
        "validation_plan": result.get("validation_plan", []),
        "open_questions": result.get("open_questions", []),
    }
