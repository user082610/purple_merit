"""
Script execution tools for the Reproduction agent.

Runs scripts in a subprocess with a timeout. Nothing clever here —
just a safe wrapper so we don't block the main process indefinitely.

We write the repro script to assessment_2/outputs/ so it persists
as a deliverable artifact.
"""

import subprocess
import sys
import time
from pathlib import Path


OUTPUTS_DIR = Path(__file__).parent.parent / "outputs"


def write_repro_script(code: str, filename: str = "repro_test.py") -> str:
    """Write the generated repro script to disk and return its path."""
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUTS_DIR / filename
    path.write_text(code, encoding="utf-8")
    return str(path)


def run_script(script_path: str, timeout_seconds: int = 30) -> dict:
    """
    Run a Python script in a subprocess and capture its output.

    Returns a dict with:
    - returncode: process exit code
    - stdout: captured stdout
    - stderr: captured stderr
    - timed_out: bool
    - duration_seconds: how long it ran
    """
    start = time.monotonic()
    timed_out = False

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(OUTPUTS_DIR),  # run from outputs dir so any generated files land there
        )
        returncode = result.returncode
        stdout = result.stdout
        stderr = result.stderr

    except subprocess.TimeoutExpired as e:
        timed_out = True
        returncode = -1
        stdout = e.stdout.decode() if e.stdout else ""
        stderr = e.stderr.decode() if e.stderr else ""
        stderr += f"\n[execution_tools] Script timed out after {timeout_seconds}s"

    except Exception as e:
        returncode = -1
        stdout = ""
        stderr = f"[execution_tools] Failed to run script: {e}"

    duration = round(time.monotonic() - start, 2)

    return {
        "returncode": returncode,
        "stdout": stdout[:4000],   # cap output — we don't need a megabyte of logs
        "stderr": stderr[:2000],
        "timed_out": timed_out,
        "duration_seconds": duration,
        "succeeded": returncode == 0,
    }


def run_pytest(test_path: str, timeout_seconds: int = 60) -> dict:
    """
    Run a pytest file and return structured results.
    Used when the repro is written as a test rather than a script.
    """
    start = time.monotonic()

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header"],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        return {
            "returncode": result.returncode,
            "output": result.stdout[:4000],
            "stderr": result.stderr[:1000],
            "passed": result.returncode == 0,
            "duration_seconds": round(time.monotonic() - start, 2),
        }

    except subprocess.TimeoutExpired:
        return {
            "returncode": -1,
            "output": "",
            "stderr": f"pytest timed out after {timeout_seconds}s",
            "passed": False,
            "duration_seconds": timeout_seconds,
        }
