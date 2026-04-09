"""
Assessment 2 orchestrator — wires the 5 agents into a LangGraph pipeline.

Flow:
  loader → triage → log_analyst → reproduction → fix_planner → critic → output

No loops in the current version. The critic can flag issues but we don't
re-run upstream agents — that would require more infrastructure than the
timeline allows. The critic's notes are included in the final output so
a human can act on them.
"""

from langgraph.graph import StateGraph, END

from assessment_2.state import BugInvestigationState
from assessment_2.agents import (
    triage_agent,
    log_analyst_agent,
    reproduction_agent,
    fix_planner_agent,
    critic_agent,
)
from assessment_2.tools.log_tools import load_bug_report, load_log_file
from shared.console import console


def load_inputs(state: BugInvestigationState) -> BugInvestigationState:
    """Load raw inputs before agents start."""
    console.print("\n[header]═══ Loading bug investigation inputs ═══[/header]")
    return {
        **state,
        "bug_report": load_bug_report(),
        "raw_logs": load_log_file(),
        "errors": [],
    }


def build_graph() -> StateGraph:
    graph = StateGraph(BugInvestigationState)

    graph.add_node("loader", load_inputs)
    graph.add_node("triage", triage_agent.run)
    graph.add_node("log_analyst", log_analyst_agent.run)
    graph.add_node("reproduction", reproduction_agent.run)
    graph.add_node("fix_planner", fix_planner_agent.run)
    graph.add_node("critic", critic_agent.run)

    graph.set_entry_point("loader")
    graph.add_edge("loader", "triage")
    graph.add_edge("triage", "log_analyst")
    graph.add_edge("log_analyst", "reproduction")
    graph.add_edge("reproduction", "fix_planner")
    graph.add_edge("fix_planner", "critic")
    graph.add_edge("critic", END)

    return graph.compile()


def run_investigation() -> BugInvestigationState:
    console.print("\n[header]╔══════════════════════════════════════╗[/header]")
    console.print("[header]║  ASSESSMENT 2 — BUG INVESTIGATION    ║[/header]")
    console.print("[header]║  BUG-2041: Task Worker Silent Failure ║[/header]")
    console.print("[header]╚══════════════════════════════════════╝[/header]\n")

    graph = build_graph()
    final_state = graph.invoke({})

    return final_state
