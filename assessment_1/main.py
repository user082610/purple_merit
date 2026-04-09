"""
Assessment 1 entry point.

Usage:
    python -m assessment_1.main
    python -m assessment_1.main --output results/launch_decision.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from rich.panel import Panel
from rich.table import Table
from rich.json import JSON

from shared.console import console
from assessment_1.orchestrator import run_war_room


def parse_args():
    parser = argparse.ArgumentParser(description="Assessment 1 — Product Launch War Room")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to write the JSON output (default: assessment_1/outputs/decision_<timestamp>.json)",
    )
    return parser.parse_args()


def display_results(state: dict) -> None:
    """Print a clean summary to the terminal."""
    decision = state["decision"]
    style_map = {"PROCEED": "decision.proceed", "PAUSE": "decision.pause", "ROLL_BACK": "decision.rollback"}
    style = style_map.get(decision, "white")

    console.print(f"\n[{style}]{'═'*50}[/{style}]")
    console.print(f"[{style}]  FINAL DECISION: {decision}[/{style}]")
    console.print(f"[{style}]{'═'*50}[/{style}]\n")

    console.print(Panel(state["rationale"], title="Rationale", border_style="cyan"))

    # Action plan table
    table = Table(title="24–48 Hour Action Plan", border_style="magenta")
    table.add_column("Priority", style="bold")
    table.add_column("Action", max_width=50)
    table.add_column("Owner")
    table.add_column("Deadline")

    for item in state.get("action_plan", []):
        table.add_row(
            item.get("priority", "—"),
            item.get("action", ""),
            item.get("owner", ""),
            item.get("deadline", ""),
        )

    console.print(table)
    console.print(f"\n[info]Confidence Score: {state.get('confidence_score', 0):.0%}[/info]")


def main():
    args = parse_args()

    try:
        final_state = run_war_room()
    except EnvironmentError as e:
        console.print(f"[bold red]Setup error:[/bold red] {e}")
        sys.exit(1)

    display_results(final_state)

    # Build the output JSON
    output = {
        "assessment": "Assessment 1 — Product Launch War Room",
        "feature": final_state["metrics_summary"]["feature"],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "decision": final_state["decision"],
        "rationale": final_state["rationale"],
        "risk_register": final_state["risk_register"],
        "action_plan": final_state["action_plan"],
        "communication_plan": final_state["communication_plan"],
        "confidence_score": final_state["confidence_score"],
        "confidence_factors": final_state["confidence_factors"],
        "agent_reports": {
            "data_analyst": final_state["analyst_report"],
            "product_manager": final_state["pm_report"],
            "marketing": final_state["marketing_report"],
            "risk_critic": final_state["critic_report"],
        },
    }

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        out_dir = Path(__file__).parent / "outputs"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = out_dir / f"decision_{ts}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    console.print(f"\n[info]✓ Full report written to: {output_path}[/info]")
    console.print(f"[info]✓ Trace log: traces/assessment_1.jsonl[/info]\n")


if __name__ == "__main__":
    main()
