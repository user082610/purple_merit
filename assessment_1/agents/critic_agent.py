"""
Risk / Critic Agent — runs last before the coordinator.

Challenges the other agents' reports. Looks for:
- Weak assumptions that haven't been stress-tested
- Missing evidence (what do we NOT know that we should?)
- Scenarios the other agents didn't consider
- Whether the proposed direction is actually safe to execute

This agent is deliberately adversarial. Its job is to poke holes, not agree.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from shared.llm import get_llm
from shared.tracer import log_step
from shared.console import console
from assessment_1.state import WarRoomState


SYSTEM_PROMPT = """You are the Risk and Reliability lead in a product war room. 
Your role is not to agree — it's to stress-test every assumption made by the other agents.

You've just read reports from the Data Analyst, Product Manager, and Marketing team.
Your job:
1. Identify the top 3-4 assumptions in their reports that are unverified or could be wrong
2. List what critical information is MISSING — what would change the recommendation if we knew it?
3. Highlight at least 2 second-order risks that nobody has mentioned yet
   (e.g. what happens downstream if we roll back? what if the issue is worse for specific user segments?)
4. Rate the rollback risk separately — rolling back isn't free, what could go wrong?
5. Give a final risk verdict: Low / Medium / High / Critical, with one sentence of justification

Be specific and pointed. This is not the place for diplomatic hedging. 
If you think the other agents missed something important, say so directly. Max 300 words."""


def run(state: WarRoomState) -> WarRoomState:
    console.print("[agent]▶ Risk/Critic Agent[/agent] — challenging assumptions...")

    context = f"""
DATA ANALYST REPORT:
{state["analyst_report"]}

PM REPORT:
{state["pm_report"]}

MARKETING REPORT:
{state["marketing_report"]}

KNOWN RISKS FROM RELEASE NOTES:
{state["release_notes"]}
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
        agent="critic_agent",
        step="risk_assessment_complete",
        payload={"report_length": len(report), "iteration": state.get("iteration", 0)},
    )

    console.print(f"[info]  ✓ Risk/Critic report ready ({len(report)} chars)[/info]")
    return {**state, "critic_report": report, "iteration": state.get("iteration", 0) + 1}
