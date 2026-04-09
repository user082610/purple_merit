"""
Data Analyst Agent — first in the pipeline.

Responsibilities:
- Interpret the aggregated metrics and anomaly detection results
- Identify which metrics are statistically significant vs normal variance
- Flag the trend direction and highlight the most concerning signals

I give this agent a fairly constrained prompt because the quantitative work
is already done by the tools. The LLM's job here is interpretation, not math.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from shared.llm import get_llm
from shared.tracer import log_step
from shared.console import console
from assessment_1.state import WarRoomState


SYSTEM_PROMPT = """You are a senior data analyst in a product war room. You have
just run anomaly detection and trend analysis on 14 days of post-launch metrics.

Your job:
1. Identify which metrics are genuinely alarming vs within normal launch variance
2. Call out the sharpest inflection points with specific dates and values
3. Flag any metrics that were trending okay early but have since deteriorated
4. Give a clear quantitative verdict: is the product healthy, borderline, or in trouble?

Be direct and specific. Reference actual numbers. Don't hedge unless the data genuinely
warrants it. Other agents will build on your analysis, so don't bury the lede.

Output format: plain paragraphs, no bullet soup. Write like you're briefing the VP of Product
in a 5-minute stand-up. Max 300 words."""


def run(state: WarRoomState) -> WarRoomState:
    console.print("[agent]▶ Data Analyst[/agent] — analyzing metrics and anomalies...")

    context = f"""
TREND SUMMARY (baseline vs recent, % change):
{json.dumps(state["trend_summary"], indent=2)}

ANOMALY FLAGS (z-score > 1.8):
{json.dumps(state["anomalies"][:10], indent=2)}

METRIC AGGREGATES:
{json.dumps(state["metrics_summary"]["metrics"], indent=2)}
""".strip()

    llm = get_llm(temperature=0.2)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = llm.invoke(messages)
    report = response.content

    log_step(
        assessment="assessment_1",
        agent="data_analyst",
        step="analysis_complete",
        payload={"report_length": len(report), "anomaly_count": len(state["anomalies"])},
    )

    console.print(f"[info]  ✓ Analyst report ready ({len(report)} chars)[/info]")
    return {**state, "analyst_report": report}
