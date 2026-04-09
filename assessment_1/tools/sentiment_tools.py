"""
Sentiment analysis tools for the Marketing agent.

These run without an LLM call — they work off the pre-labeled sentiment
in the dataset. In a real system you'd call a classifier here, but for
this assessment the labels are already there and I'd rather spend the
LLM tokens on reasoning than re-classifying data that's already labeled.
"""

from assessment_1.tools.metric_tools import load_feedback
from collections import Counter


def summarize_sentiment() -> dict:
    """
    Count sentiment labels and bucket feedback by date range.
    """
    feedback = load_feedback()

    label_counts = Counter(f["sentiment_label"] for f in feedback)
    total = len(feedback)

    # Split into early (first 7 days) vs late (last 7 days)
    # The launch was 2026-03-27, so cutoff is 2026-04-03
    early = [f for f in feedback if f["date"] < "2026-04-03"]
    late = [f for f in feedback if f["date"] >= "2026-04-03"]

    return {
        "total_entries": total,
        "overall": {
            "positive": label_counts.get("positive", 0),
            "neutral": label_counts.get("neutral", 0),
            "negative": label_counts.get("negative", 0),
        },
        "early_window": {
            "positive": sum(1 for f in early if f["sentiment_label"] == "positive"),
            "neutral": sum(1 for f in early if f["sentiment_label"] == "neutral"),
            "negative": sum(1 for f in early if f["sentiment_label"] == "negative"),
        },
        "late_window": {
            "positive": sum(1 for f in late if f["sentiment_label"] == "positive"),
            "neutral": sum(1 for f in late if f["sentiment_label"] == "neutral"),
            "negative": sum(1 for f in late if f["sentiment_label"] == "negative"),
        },
    }


def extract_top_issues(n: int = 5) -> list[str]:
    """
    Pull out the most representative negative feedback texts.
    Simple approach: return the most recent negatives.
    """
    feedback = load_feedback()
    negatives = [f["text"] for f in feedback if f["sentiment_label"] == "negative"]
    # Take a spread across dates rather than just the last N
    step = max(1, len(negatives) // n)
    return negatives[::step][:n]


def get_feedback_timeline() -> list[dict]:
    """Return daily sentiment breakdown for Marketing agent's trend analysis."""
    feedback = load_feedback()
    by_date: dict[str, Counter] = {}

    for f in feedback:
        date = f["date"]
        if date not in by_date:
            by_date[date] = Counter()
        by_date[date][f["sentiment_label"]] += 1

    return [
        {
            "date": date,
            "positive": counts.get("positive", 0),
            "neutral": counts.get("neutral", 0),
            "negative": counts.get("negative", 0),
        }
        for date, counts in sorted(by_date.items())
    ]
