"""
Coordinator Agent — synthesizes all four agent reports into a final structured decision.

This is the "output node" of the graph. It doesn't do any new analysis —
it aggregates the war room discussion into a clean, actionable JSON output.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser

from shared.llm import get_llm
from shared.tracer import log_step
from shared.console import console
from assessment_1.state import WarRoomState


SYSTEM_PROMPT = """You are the war room coordinator. All four agents have reported.
Your job is to synthesize their findings into a final structured decision.

You MUST produce valid JSON matching this exact schema:
{
  "decision": "PROCEED" | "PAUSE" | "ROLL_BACK",
  "rationale": "2-3 sentence explanation referencing specific metric findings and agent inputs",
  "risk_register": [
    {
      "risk": "brief risk title",
      "severity": "Low" | "Medium" | "High" | "Critical",
      "likelihood": "Low" | "Medium" | "High",
      "mitigation": "specific action to reduce this risk"
    }
  ],
  "action_plan": [
    {
      "action": "specific action item",
      "owner": "team or role responsible",
      "deadline": "e.g. within 2 hours / by end of day / within 48 hours",
      "priority": "P0" | "P1" | "P2"
    }
  ],
  "communication_plan": {
    "internal": "message for engineering/leadership",
    "external": "message for users (in-app or email)"
  },
  "confidence_score": 0.0 to 1.0,
  "confidence_factors": ["list of strings — what would increase or decrease confidence"]
}

Return ONLY the JSON object. No markdown. No explanation outside the JSON."""


def run(state: WarRoomState) -> WarRoomState:
    console.print("[agent]▶ Coordinator[/agent] — synthesizing final decision...")

    context = f"""
ANALYST REPORT:
{state["analyst_report"]}

PM REPORT:
{state["pm_report"]}

MARKETING REPORT:
{state["marketing_report"]}

RISK/CRITIC REPORT:
{state["critic_report"]}

KEY METRICS TODAY:
- Crash rate: {state["metrics_summary"]["metrics"]["crash_rate"]["recent_avg"]:.2%} (was {state["metrics_summary"]["metrics"]["crash_rate"]["baseline_avg"]:.2%} at launch)
- API p95: {state["metrics_summary"]["metrics"]["api_p95_ms"]["recent_avg"]:.0f}ms (was {state["metrics_summary"]["metrics"]["api_p95_ms"]["baseline_avg"]:.0f}ms at launch)
- Payment failure rate: {state["metrics_summary"]["metrics"]["payment_failure_rate"]["recent_avg"]:.1%} (was {state["metrics_summary"]["metrics"]["payment_failure_rate"]["baseline_avg"]:.1%} at launch)
- Support tickets today: ~{state["metrics_summary"]["metrics"]["support_tickets"]["recent_avg"]:.0f} (was ~{state["metrics_summary"]["metrics"]["support_tickets"]["baseline_avg"]:.0f} at launch)
""".strip()

    llm = get_llm(temperature=0.1)  # low temp for the final decision — determinism matters here
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = llm.invoke(messages)

    # Parse the JSON — if it fails we still want the raw text logged
    try:
        result = json.loads(response.content)
    except json.JSONDecodeError:
        # Try to extract JSON block if there's surrounding text
        import re
        match = re.search(r'\{.*\}', response.content, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            raise ValueError(f"Coordinator returned unparseable response: {response.content[:200]}")

    log_step(
        assessment="assessment_1",
        agent="coordinator",
        step="decision_made",
        payload={"decision": result.get("decision"), "confidence": result.get("confidence_score")},
    )

    console.print(
        f"\n[bold]War Room Decision:[/bold] "
        f"[decision.{result['decision'].lower()}]{result['decision']}[/decision.{result['decision'].lower()}] "
        f"(confidence: {result.get('confidence_score', 0):.0%})"
    )

    return {
        **state,
        "decision": result["decision"],
        "rationale": result["rationale"],
        "risk_register": result["risk_register"],
        "action_plan": result["action_plan"],
        "communication_plan": result["communication_plan"],
        "confidence_score": result["confidence_score"],
        "confidence_factors": result["confidence_factors"],
    }
