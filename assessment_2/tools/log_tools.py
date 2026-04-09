"""
Log parsing tools for the Log Analyst agent.

These do the mechanical work — extract stack traces, find error signatures,
identify repeated patterns — so the LLM only has to interpret, not grep.
"""

import re
from pathlib import Path
from collections import defaultdict


INPUTS_DIR = Path(__file__).parent.parent / "inputs"


def load_log_file() -> str:
    with open(INPUTS_DIR / "app.log") as f:
        return f.read()


def load_bug_report() -> str:
    with open(INPUTS_DIR / "bug_report.md") as f:
        return f.read()


def extract_stack_traces(log_text: str) -> list[dict]:
    """
    Parse multi-line stack traces out of the log.

    Heuristic: a stack trace starts with a Traceback line and ends when
    we hit a non-indented line that isn't part of the exception message.
    This is good enough for Python tracebacks — wouldn't work for Java.
    """
    traces = []
    lines = log_text.splitlines()
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for the start of a traceback
        if "Traceback (most recent call last)" in line:
            trace_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i]
                # Keep consuming lines that look like part of the trace
                if (next_line.startswith("  ") or
                        next_line.startswith("File") or
                        re.match(r'\w+Error|Exception', next_line.lstrip()) or
                        next_line.strip().startswith("sqlalchemy") or
                        not next_line.strip()):
                    trace_lines.append(next_line)
                    i += 1
                else:
                    break

            # Extract metadata from the log line before the Traceback
            timestamp = ""
            worker = ""
            if i - len(trace_lines) - 1 >= 0:
                prev = lines[i - len(trace_lines) - 1]
                ts_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', prev)
                if ts_match:
                    timestamp = ts_match.group(1)
                w_match = re.search(r'\[(\w+-\d+)\]', prev)
                if w_match:
                    worker = w_match.group(1)

            traces.append({
                "timestamp": timestamp,
                "worker": worker,
                "trace": "\n".join(trace_lines),
                "error_type": _extract_error_type(trace_lines),
            })

        else:
            i += 1

    return traces


def _extract_error_type(trace_lines: list[str]) -> str:
    """Get the exception class name from the last meaningful line of a trace."""
    for line in reversed(trace_lines):
        line = line.strip()
        match = re.match(r'(\w+(?:\.\w+)*Error|\w+Exception):', line)
        if match:
            return match.group(1)
    return "UnknownError"


def extract_error_signatures(log_text: str) -> list[dict]:
    """
    Find all ERROR and WARNING lines, count duplicates, and return a
    frequency-sorted list. Useful for spotting which errors are systematic
    vs one-offs.
    """
    lines = log_text.splitlines()
    signature_counts: dict[str, int] = defaultdict(int)
    signature_examples: dict[str, str] = {}

    for line in lines:
        if " ERROR " in line or " WARNING " in line:
            # Strip timestamp + worker to normalize — we want to count
            # the same error from different workers as one signature
            normalized = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', '', line)
            normalized = re.sub(r'\[worker-\d+\]', '[worker-N]', normalized)
            normalized = re.sub(r'task-\d+', 'task-X', normalized)
            normalized = normalized.strip()

            signature_counts[normalized] += 1
            if normalized not in signature_examples:
                signature_examples[normalized] = line.strip()

    return sorted(
        [
            {
                "signature": sig,
                "count": count,
                "example": signature_examples[sig],
                "level": "ERROR" if " ERROR " in signature_examples[sig] else "WARNING",
            }
            for sig, count in signature_counts.items()
        ],
        key=lambda x: x["count"],
        reverse=True,
    )


def find_double_pickup_events(log_text: str) -> list[dict]:
    """
    Find cases where two workers picked up the same task ID.
    This is the smoking gun for the race condition.
    """
    lines = log_text.splitlines()
    pickup_map: dict[str, list[str]] = defaultdict(list)

    for line in lines:
        match = re.search(r'\[(\w+-\d+)\].*picked up task (task-\d+)', line)
        if match:
            worker = match.group(1)
            task_id = match.group(2)
            pickup_map[task_id].append(worker)

    duplicates = []
    for task_id, workers in pickup_map.items():
        if len(workers) > 1:
            duplicates.append({
                "task_id": task_id,
                "workers": workers,
                "note": "Same task picked up by multiple workers — race condition confirmed",
            })

    return duplicates


def get_relevant_log_lines(log_text: str, keywords: list[str]) -> list[dict]:
    """
    Return log lines containing any of the given keywords, with line numbers.
    Used by the Log Analyst to build its evidence bundle.
    """
    lines = log_text.splitlines()
    results = []

    for i, line in enumerate(lines, start=1):
        if any(kw.lower() in line.lower() for kw in keywords):
            results.append({"line_num": i, "content": line.strip()})

    return results
