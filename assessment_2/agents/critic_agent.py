"""
Reviewer / Critic Agent — final stage of Assessment 2.

Challenges the fix plan from three angles:
1. Is the root cause actually correct, or are we treating a symptom?
2. Is the repro actually minimal? (or does it hide complexity?)
3. Is the patch safe to ship without breaking something else?

Also flags edge cases the Fix Planner didn't mention.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from shared.llm import get_llm
from shared.tracer import log_step
from shared.console import console
from assessment_2.state import BugInvestigationState


SYSTEM_PROMPT = """You are a senior engineer doing a critical review of a bug investigation and fix plan.

Your job is NOT to agree. Challenge weak assumptions, find gaps, and think about edge cases.

Review the investigation across three dimensions:

1. ROOT CAUSE VALIDITY
   - Is the stated root cause truly the root cause, or a symptom?
   - Is the confidence score justified?
   - What alternative root causes weren't fully ruled out?

2. REPRO QUALITY
   - Does the repro actually test the exact failure path from production?
   - Is it truly minimal, or does it inadvertently hide complexity?
   - What would make it more reliable?

3. PATCH SAFETY
   - Could the proposed patch break something else?
   - Are there edge cases (e.g. partial failures, restart mid-fix, rollback scenarios)?
   - Is the validation plan sufficient to catch regressions?

Output a JSON object:
{
  "approved": true | false,
  "overall_assessment": "2-3 sentences",
  "root_cause_challenges": ["specific challenges to the root cause analysis"],
  "repro_notes": ["observations about the repro quality"],
  "patch_risks": ["specific risks in the proposed patch — reference actual patch items"],
  "missed_edge_cases": ["edge cases the fix planner didn't mention"],
  "recommended_additions": ["what to add to the patch or validation plan"]
}

Be direct. If the plan is solid, say so and approve — but still note anything worth watching.
Return only JSON."""


def run(state: BugInvestigationState) -> BugInvestigationState:
    console.print("[agent]▶ Reviewer/Critic[/agent] — reviewing fix plan for gaps and risks...")

    context = f"""
ROOT CAUSE STATED:
{state.get("root_cause")}
Confidence: {state.get("root_cause_confidence", 0):.0%}

PATCH PLAN:
{json.dumps(state.get("patch_plan", []), indent=2)}

VALIDATION PLAN:
{json.dumps(state.get("validation_plan", []), indent=2)}

OPEN QUESTIONS FROM FIX PLANNER:
{json.dumps(state.get("open_questions", []), indent=2)}

REPRO RESULT:
- Reproduced: {state.get("repro_succeeded")}
- Output (truncated): {state.get("repro_run_output", "")[:400]}

TRIAGE HYPOTHESES NOT YET CONFIRMED OR DENIED:
{json.dumps([h for h in state.get("hypotheses", []) if h.get("confidence") != "High"], indent=2)}
""".strip()

    llm = get_llm(temperature=0.3)
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
        result = json.loads(match.group()) if match else {"approved": False}

    approved = result.get("approved", False)

    log_step(
        assessment="assessment_2",
        agent="critic",
        step="review_complete",
        payload={
            "approved": approved,
            "patch_risks_flagged": len(result.get("patch_risks", [])),
        },
    )

    status = "[bold green]APPROVED[/bold green]" if approved else "[bold yellow]APPROVED WITH NOTES[/bold yellow]"
    console.print(f"  {status} — {result.get('overall_assessment', '')[:80]}...")

    return {
        **state,
        "critic_feedback": json.dumps(result, indent=2),
        "critic_approved": approved,
    }
