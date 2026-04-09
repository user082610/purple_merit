"""
Reproduction Agent — generates a minimal repro script then actually runs it.

This agent does two LLM calls:
1. Generate the repro script code
2. After running it, interpret the output and confirm if the bug was reproduced

The script is deliberately minimal — no Flask, no Redis required.
We simulate the race using threads and a shared dict, which is enough to
demonstrate the IntegrityError-swallow pattern without any infrastructure.
"""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from shared.llm import get_llm
from shared.tracer import log_step, log_tool_call
from shared.console import console
from assessment_2.state import BugInvestigationState
from assessment_2.tools.execution_tools import write_repro_script, run_script


GENERATION_SYSTEM_PROMPT = """You are a senior engineer writing a minimal reproducible test case for a bug.

The bug is a race condition in a Python task worker:
- Multiple threads concurrently dequeue and process the same task
- When two workers try to write the result for the same task_id, one gets an IntegrityError
- The IntegrityError is swallowed (caught and ignored)
- The swallowing worker ALSO skips updating the task status — so the task stays 'processing' forever

Write a self-contained Python script (no external dependencies — only stdlib) that:
1. Simulates the buggy dequeue + write pattern using sqlite3 and threading
2. Demonstrates that tasks end up stuck in 'processing' state
3. Prints clear PASS/FAIL output at the end
4. Completes in under 10 seconds

Requirements:
- Use only Python stdlib (sqlite3, threading, time, random — nothing else)
- The bug should fail CONSISTENTLY (not intermittently) — use time.sleep() to make the race deterministic
- Add a comment at the top: "# REPRO for BUG-2041 — task worker race condition"
- Print [REPRO CONFIRMED] if tasks are stuck, [NOT REPRODUCED] if all tasks complete

Return ONLY the Python code. No explanation, no markdown fences."""

INTERPRETATION_SYSTEM_PROMPT = """You ran a bug reproduction script. Interpret the output.

Answer with a JSON object:
{
  "reproduced": true | false,
  "summary": "one sentence — what the output shows",
  "stuck_task_count": <number or null>,
  "notes": "any notable behavior in the output beyond the basic pass/fail"
}

Return only JSON."""


def run(state: BugInvestigationState) -> BugInvestigationState:
    console.print("[agent]▶ Reproduction Agent[/agent] — generating and running repro script...")

    # Step 1: Generate the repro script
    context = f"""
TRIAGE SUMMARY:
- Symptoms: {', '.join(state['symptoms'][:3])}
- Hypotheses (top): {state['hypotheses'][0]['hypothesis'] if state['hypotheses'] else 'none'}

LOG ANALYST FINDINGS:
- Anomaly pattern: {state.get('anomaly_pattern', 'not yet analyzed')}
- Double pickups confirmed: {len([e for e in state.get('log_evidence', []) if 'duplicate' in e.get('content', '').lower()])} events
"""

    llm = get_llm(temperature=0.1)  # low temp — we want deterministic, runnable code
    gen_messages = [
        SystemMessage(content=GENERATION_SYSTEM_PROMPT),
        HumanMessage(content=context.strip()),
    ]

    code_response = llm.invoke(gen_messages)
    repro_code = code_response.content.strip()

    # Strip markdown fences if the LLM added them anyway
    if repro_code.startswith("```"):
        lines = repro_code.split("\n")
        repro_code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # Step 2: Write and run the repro
    script_path = write_repro_script(repro_code)
    log_tool_call("assessment_2", "reproduction", "write_repro_script", {"path": script_path}, {})

    console.print(f"[info]  ▷ Running repro script at {script_path}...[/info]")
    run_result = run_script(script_path, timeout_seconds=20)
    log_tool_call("assessment_2", "reproduction", "run_script", {"path": script_path}, run_result)

    console.print(
        f"[info]  ✓ Script ran in {run_result['duration_seconds']}s "
        f"(exit code: {run_result['returncode']})[/info]"
    )

    # Step 3: Interpret the output
    combined_output = f"STDOUT:\n{run_result['stdout']}\n\nSTDERR:\n{run_result['stderr']}"
    interp_messages = [
        SystemMessage(content=INTERPRETATION_SYSTEM_PROMPT),
        HumanMessage(content=combined_output),
    ]

    interp_response = llm.invoke(interp_messages)
    try:
        interpretation = json.loads(interp_response.content)
    except json.JSONDecodeError:
        import re
        match = re.search(r'\{.*\}', interp_response.content, re.DOTALL)
        interpretation = json.loads(match.group()) if match else {"reproduced": False, "summary": "parse error"}

    repro_succeeded = interpretation.get("reproduced", False)
    repro_output = combined_output[:2000]

    log_step(
        assessment="assessment_2",
        agent="reproduction",
        step="repro_complete",
        payload={
            "reproduced": repro_succeeded,
            "exit_code": run_result["returncode"],
            "summary": interpretation.get("summary", ""),
        },
    )

    status = "[bold green]✓ BUG REPRODUCED[/bold green]" if repro_succeeded else "[bold yellow]⚠ Not reproduced[/bold yellow]"
    console.print(f"  {status} — {interpretation.get('summary', '')}")

    return {
        **state,
        "repro_script_path": script_path,
        "repro_script_code": repro_code,
        "repro_run_output": repro_output,
        "repro_succeeded": repro_succeeded,
    }
