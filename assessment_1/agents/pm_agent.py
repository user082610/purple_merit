"""
Product Manager Agent — runs after the Data Analyst.

Responsibilities:
- Define what "success" looked like for this launch
- Evaluate the analyst's findings against those success criteria
- Frame the user impact in business terms (not just metrics)
- Propose a preliminary go/no-go leaning with reasoning

The PM thinks in terms of user outcomes and business goals, not z-scores.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from shared.llm import get_llm
from shared.tracer import log_step
from shared.console import console
from assessment_1.state import WarRoomState


SYSTEM_PROMPT = """You are the Product Manager for a feature called "Express Checkout v2".
You've been in this war room for the past hour reviewing the launch.

Your job in this report:
1. State what the original success criteria were for this launch (you can infer reasonable ones
   from the context — e.g. checkout conversion, D1 retention, crash rate thresholds)
2. Evaluate each criterion: met / at risk / failed
3. Quantify the user impact — how many users are affected by the degradation?
4. Give your preliminary lean: Proceed, Pause, or Roll Back — and why
5. What additional information would change your answer?

You've read the analyst's technical report. Factor it in but speak in product terms.
Don't repeat numbers already stated — reference them with context instead.

Be opinionated. You own this feature. Max 300 words."""


def run(state: WarRoomState) -> WarRoomState:
    console.print("[agent]▶ PM Agent[/agent] — evaluating against success criteria...")

    context = f"""
FEATURE: {state["metrics_summary"]["feature"]}
DAYS SINCE LAUNCH: {state["metrics_summary"]["total_days"]}

ANALYST REPORT:
{state["analyst_report"]}

RELEASE NOTES (known risks at launch):
{state["release_notes"]}

CURRENT DAU: {state["metrics_summary"]["metrics"]["dau"]["recent_avg"]:.0f}
CURRENT PAYMENT FAILURE RATE: {state["metrics_summary"]["metrics"]["payment_failure_rate"]["recent_avg"]:.1%}
CURRENT CRASH RATE: {state["metrics_summary"]["metrics"]["crash_rate"]["recent_avg"]:.1%}
""".strip()

    llm = get_llm(temperature=0.3)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = llm.invoke(messages)
    report = response.content

    log_step(
        assessment="assessment_1",
        agent="pm_agent",
        step="evaluation_complete",
        payload={"report_length": len(report)},
    )

    console.print(f"[info]  ✓ PM report ready ({len(report)} chars)[/info]")
    return {**state, "pm_report": report}
