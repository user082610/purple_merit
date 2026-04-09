"""
Assessment 2 entry point.

Usage:
    python -m assessment_2.main
    python -m assessment_2.main --output path/to/report.yaml
"""

import argparse
import json
import sys
import yaml
from datetime import datetime
from pathlib import Path

from rich.panel import Panel
from rich.table import Table

from shared.console import console
from assessment_2.orchestrator import run_investigation


def parse_args():
    parser = argparse.ArgumentParser(description="Assessment 2 — Automated Bug Investigation")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to write the YAML output (default: assessment_2/outputs/report_<timestamp>.yaml)",
    )
    return parser.parse_args()


def display_results(state: dict) -> None:
    console.print("\n[bold cyan]══ Investigation Summary ══[/bold cyan]\n")

    console.print(Panel(
        f"[bold]{state.get('root_cause', 'No root cause identified')}[/bold]\n"
        f"Confidence: {state.get('root_cause_confidence', 0):.0%}",
        title="Root Cause",
        border_style="red",
    ))

    # Patch plan table
    patch_table = Table(title="Patch Plan", border_style="yellow")
    patch_table.add_column("File/Module", style="bold")
    patch_table.add_column("Change", max_width=50)
    patch_table.add_column("Risk")

    for item in state.get("patch_plan", []):
        patch_table.add_row(
            item.get("file", "—"),
            item.get("change", ""),
            item.get("risk", "—"),
        )

    console.print(patch_table)

    repro_status = (
        "[bold green]✓ Reproduced[/bold green]"
        if state.get("repro_succeeded")
        else "[bold yellow]⚠ Not reproduced[/bold yellow]"
    )
    console.print(f"\nRepro script: {repro_status}")
    console.print(f"Repro path:   [info]{state.get('repro_script_path', '—')}[/info]")
    console.print(f"Critic approved: {'✓' if state.get('critic_approved') else '⚠ See notes'}")


def main():
    args = parse_args()

    try:
        final_state = run_investigation()
    except EnvironmentError as e:
        console.print(f"[bold red]Setup error:[/bold red] {e}")
        sys.exit(1)

    display_results(final_state)

    # Build the final YAML report
    report = {
        "assessment": "Assessment 2 — Automated Bug Investigation",
        "bug_id": "BUG-2041",
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "bug_summary": {
            "title": "Background task jobs silently fail without error or retry",
            "symptoms": final_state.get("symptoms", []),
            "expected_behavior": final_state.get("expected_behavior", ""),
            "actual_behavior": final_state.get("actual_behavior", ""),
            "severity": final_state.get("severity", ""),
            "environment": final_state.get("environment", {}),
        },
        "evidence": {
            "stack_traces": final_state.get("stack_traces", []),
            "error_signatures": final_state.get("error_signatures", []),
            "relevant_log_lines": final_state.get("log_evidence", [])[:10],
            "anomaly_pattern": final_state.get("anomaly_pattern", ""),
        },
        "repro": {
            "script_path": final_state.get("repro_script_path", ""),
            "run_command": f"python {final_state.get('repro_script_path', 'assessment_2/outputs/repro_test.py')}",
            "reproduced": final_state.get("repro_succeeded", False),
            "output_summary": final_state.get("repro_run_output", "")[:800],
        },
        "root_cause": {
            "hypothesis": final_state.get("root_cause", ""),
            "confidence": final_state.get("root_cause_confidence", 0),
            "hypotheses_considered": final_state.get("hypotheses", []),
        },
        "patch_plan": final_state.get("patch_plan", []),
        "validation_plan": final_state.get("validation_plan", []),
        "open_questions": final_state.get("open_questions", []),
        "critic_review": {
            "approved": final_state.get("critic_approved", False),
            "feedback": json.loads(final_state.get("critic_feedback", "{}")),
        },
    }

    # Write output
    if args.output:
        output_path = Path(args.output)
    else:
        out_dir = Path(__file__).parent / "outputs"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_path = out_dir / f"report_{ts}.yaml"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        yaml.dump(report, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    console.print(f"\n[info]✓ Full report written to: {output_path}[/info]")
    console.print(f"[info]✓ Repro script:           {final_state.get('repro_script_path', '—')}[/info]")
    console.print(f"[info]✓ Trace log:              traces/assessment_2.jsonl[/info]\n")


if __name__ == "__main__":
    main()
