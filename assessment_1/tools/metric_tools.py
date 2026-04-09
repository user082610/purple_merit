"""
Metric aggregation and anomaly detection tools for the Data Analyst agent.

I kept these as pure functions rather than LangChain tools so they're easier
to test in isolation and the agent can call them directly. The tool → agent
boundary is enforced at the orchestrator level.
"""

import json
import statistics
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).parent.parent / "data"


def load_metrics() -> dict:
    with open(DATA_DIR / "metrics.json") as f:
        return json.load(f)


def load_feedback() -> list[dict]:
    with open(DATA_DIR / "user_feedback.json") as f:
        return json.load(f)


def load_release_notes() -> str:
    with open(DATA_DIR / "release_notes.md") as f:
        return f.read()


def aggregate_metrics() -> dict[str, Any]:
    """
    Compute summary stats for each metric across the 14-day window.
    Returns baseline (first 4 days) vs recent (last 4 days) for easy comparison.
    """
    data = load_metrics()
    days = data["days"]

    fields = [
        "activation_rate", "dau", "d1_retention", "d7_retention",
        "crash_rate", "api_p95_ms", "payment_success_rate",
        "payment_failure_rate", "support_tickets", "feature_funnel_completion",
        "churn_rate"
    ]

    baseline = days[:4]
    recent = days[-4:]

    result = {"feature": data["feature"], "total_days": len(days), "metrics": {}}

    for field in fields:
        baseline_vals = [d[field] for d in baseline]
        recent_vals = [d[field] for d in recent]
        all_vals = [d[field] for d in days]

        result["metrics"][field] = {
            "baseline_avg": round(statistics.mean(baseline_vals), 4),
            "recent_avg": round(statistics.mean(recent_vals), 4),
            "overall_avg": round(statistics.mean(all_vals), 4),
            "min": round(min(all_vals), 4),
            "max": round(max(all_vals), 4),
            "trend": "up" if recent_vals[-1] > baseline_vals[0] else "down",
        }

    return result


def detect_anomalies(zscore_threshold: float = 1.8) -> list[dict]:
    """
    Simple z-score anomaly detection over the time series.
    Flags days where any metric deviates more than `zscore_threshold` standard
    deviations from the series mean.

    A threshold of 1.8 is slightly looser than the classic 2.0 — fine for
    operational monitoring where you'd rather investigate a false positive
    than miss a real incident.
    """
    data = load_metrics()
    days = data["days"]

    watch_fields = [
        "crash_rate", "api_p95_ms", "payment_failure_rate", "support_tickets"
    ]

    anomalies = []

    for field in watch_fields:
        vals = [d[field] for d in days]
        mean = statistics.mean(vals)
        stdev = statistics.stdev(vals) if len(vals) > 1 else 0

        if stdev == 0:
            continue

        for day in days:
            z = (day[field] - mean) / stdev
            if abs(z) > zscore_threshold:
                anomalies.append({
                    "date": day["date"],
                    "metric": field,
                    "value": day[field],
                    "z_score": round(z, 2),
                    "direction": "high" if z > 0 else "low",
                })

    return sorted(anomalies, key=lambda x: abs(x["z_score"]), reverse=True)


def compute_trend_summary() -> dict:
    """
    Returns a plain-English summary of metric directions for the LLM to reason over.
    """
    agg = aggregate_metrics()
    summary = {}

    for metric, stats in agg["metrics"].items():
        delta_pct = 0
        if stats["baseline_avg"] != 0:
            delta_pct = ((stats["recent_avg"] - stats["baseline_avg"]) / stats["baseline_avg"]) * 100

        summary[metric] = {
            "direction": stats["trend"],
            "change_pct": round(delta_pct, 1),
            "baseline": stats["baseline_avg"],
            "recent": stats["recent_avg"],
        }

    return summary
