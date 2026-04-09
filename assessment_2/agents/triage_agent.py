"""
Triage Agent — first in the Assessment 2 pipeline.

Reads the raw bug report and extracts structured information:
- Symptoms (what's observable)
- Expected vs actual behavior
- Environment details
- Prioritized hypotheses (what we think might be causing this)

The goal is to give downstream agents a clean, structured starting point
instead of everyone re-parsing the raw markdown.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from shared.llm import get_llm
from shared.tracer import log_step
from shared.console import console
from assessment_2.state import BugInvestigationState


SYSTEM_PROMPT = """You are a senior engineer doing first-pass triage on a bug report.

Your job is to extract structured information from the raw report and think critically
about what's most likely going on. Don't just re-summarize — add your own assessment.

Output ONLY a valid JSON object with this exact structure:
{
  "symptoms": ["list of observable symptoms — specific, not vague"],
  "expected_behavior": "one sentence — what should happen",
  "actual_behavior": "one sentence — what is actually happening",
  "environment": {
    "language": "...",
    "runtime_version": "...",
    "relevant_deps": "...",
    "concurrency_model": "...",
    "deployment": "..."
  },
  "severity": "Low | Medium | High | Critical",
  "severity_rationale": "one sentence",
  "hypotheses": [
    {
      "hypothesis": "specific technical hypothesis",
      "confidence": "Low | Medium | High",
      "rationale": "why this is plausible based on the report"
    }
  ]
}

Prioritize hypotheses by confidence. Include 3-4 hypotheses — even low-confidence ones
are worth tracking. No markdown, no explanation outside the JSON."""


def run(state: BugInvestigationState) -> BugInvestigationState:
    console.print("[agent]▶ Triage Agent[/agent] — parsing bug report and forming hypotheses...")

    llm = get_llm(temperature=0.2)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"BUG REPORT:\n\n{state['bug_report']}"),
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
        agent="triage",
        step="triage_complete",
        payload={
            "severity": result.get("severity"),
            "hypothesis_count": len(result.get("hypotheses", [])),
        },
    )

    console.print(f"[info]  ✓ Triage done — severity: {result.get('severity')}, "
                  f"{len(result.get('hypotheses', []))} hypotheses formed[/info]")

    return {
        **state,
        "symptoms": result.get("symptoms", []),
        "expected_behavior": result.get("expected_behavior", ""),
        "actual_behavior": result.get("actual_behavior", ""),
        "environment": result.get("environment", {}),
        "hypotheses": result.get("hypotheses", []),
        "severity": result.get("severity", "High"),
    }
