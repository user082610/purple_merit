"""
Assessment 1 orchestrator — wires the agents into a LangGraph state machine.

Flow:
  loader → data_analyst → pm → marketing → critic → coordinator

The critic doesn't loop back in this implementation (single pass is sufficient
for the data we have), but the iteration counter in state makes it easy to add
a loop condition later if needed.
"""

from langgraph.graph import StateGraph, END

from assessment_1.state import WarRoomState
from assessment_1.agents import (
    data_analyst_agent,
    pm_agent,
    marketing_agent,
    critic_agent,
    coordinator_agent,
)
from assessment_1.tools.metric_tools import (
    aggregate_metrics,
    detect_anomalies,
    compute_trend_summary,
    load_release_notes,
)
from assessment_1.tools.sentiment_tools import (
    summarize_sentiment,
    extract_top_issues,
    get_feedback_timeline,
)
from shared.console import console


def load_inputs(state: WarRoomState) -> WarRoomState:
    """Load and pre-compute all tool outputs before agents start."""
    console.print("\n[header]═══ Loading war room data ═══[/header]")
    return {
        **state,
        "metrics_summary": aggregate_metrics(),
        "anomalies": detect_anomalies(),
        "trend_summary": compute_trend_summary(),
        "sentiment_summary": summarize_sentiment(),
        "top_issues": extract_top_issues(n=6),
        "sentiment_timeline": get_feedback_timeline(),
        "release_notes": load_release_notes(),
        "iteration": 0,
        "errors": [],
    }


def build_graph() -> StateGraph:
    graph = StateGraph(WarRoomState)

    graph.add_node("loader", load_inputs)
    graph.add_node("data_analyst", data_analyst_agent.run)
    graph.add_node("pm", pm_agent.run)
    graph.add_node("marketing", marketing_agent.run)
    graph.add_node("critic", critic_agent.run)
    graph.add_node("coordinator", coordinator_agent.run)

    graph.set_entry_point("loader")
    graph.add_edge("loader", "data_analyst")
    graph.add_edge("data_analyst", "pm")
    graph.add_edge("pm", "marketing")
    graph.add_edge("marketing", "critic")
    graph.add_edge("critic", "coordinator")
    graph.add_edge("coordinator", END)

    return graph.compile()


def run_war_room() -> WarRoomState:
    console.print("\n[header]╔══════════════════════════════════════╗[/header]")
    console.print("[header]║   ASSESSMENT 1 — WAR ROOM SYSTEM     ║[/header]")
    console.print("[header]║   Express Checkout v2 Launch Review  ║[/header]")
    console.print("[header]╚══════════════════════════════════════╝[/header]\n")

    graph = build_graph()
    final_state = graph.invoke({})  # initial state is empty; loader fills it

    return final_state
