"""
Marketing / Comms Agent — runs after the PM.

Responsibilities:
- Assess the sentiment trajectory and what it signals about public perception
- Identify the key messages users are amplifying (positive or negative)
- Draft what internal and external communication should say right now
- Flag any reputation or trust risks that the other agents may have missed
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from shared.llm import get_llm
from shared.tracer import log_step
from shared.console import console
from assessment_1.state import WarRoomState


SYSTEM_PROMPT = """You are the Head of Marketing / Customer Communications at a product company.
A feature launch is in trouble and you're in the war room.

Your job:
1. Interpret the sentiment trend — not just the overall numbers, but the trajectory
   (early sentiment vs recent sentiment tells a different story than the average)
2. Identify the top 2-3 themes in negative feedback that users are most vocal about
3. Assess the trust and reputation risk if the situation continues another 48 hours
4. Draft brief internal and external messaging for the next 24 hours:
   - Internal: what to tell the team and leadership
   - External: what to post to users (in-app banner, email, or social — your call on channel)
5. Flag any PR risks the other agents haven't addressed

Keep the draft messages real — write them like a comms professional would, not like
a corporate press release. Max 350 words total."""


def run(state: WarRoomState) -> WarRoomState:
    console.print("[agent]▶ Marketing Agent[/agent] — assessing sentiment and comms risk...")

    sentiment = state["sentiment_summary"]
    timeline = state["sentiment_timeline"]

    # Build a readable summary of the sentiment shift
    early_neg_pct = 0
    late_neg_pct = 0
    early = sentiment["early_window"]
    late = sentiment["late_window"]
    early_total = sum(early.values()) or 1
    late_total = sum(late.values()) or 1
    early_neg_pct = early["negative"] / early_total * 100
    late_neg_pct = late["negative"] / late_total * 100

    context = f"""
SENTIMENT OVERVIEW:
- Total feedback entries: {sentiment["total_entries"]}
- Overall: {sentiment["overall"]["positive"]} positive, {sentiment["overall"]["neutral"]} neutral, {sentiment["overall"]["negative"]} negative
- Early launch (days 1-7): {early_neg_pct:.0f}% negative
- Recent (days 8-14): {late_neg_pct:.0f}% negative

SAMPLE NEGATIVE FEEDBACK:
{chr(10).join(f'- "{issue}"' for issue in state["top_issues"])}

PM ASSESSMENT:
{state["pm_report"][:400]}

DAILY SENTIMENT TIMELINE:
{json.dumps(timeline, indent=2)}
""".strip()

    llm = get_llm(temperature=0.4)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = llm.invoke(messages)
    report = response.content

    log_step(
        assessment="assessment_1",
        agent="marketing_agent",
        step="comms_assessment_complete",
        payload={
            "early_neg_pct": round(early_neg_pct, 1),
            "late_neg_pct": round(late_neg_pct, 1),
            "report_length": len(report),
        },
    )

    console.print(f"[info]  ✓ Marketing report ready ({len(report)} chars)[/info]")
    return {**state, "marketing_report": report}
