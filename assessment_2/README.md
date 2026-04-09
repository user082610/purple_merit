# Assessment 2 — Automated Bug Investigation

A multi-agent system that ingests a bug report and application logs, attempts to reproduce
the failure, and produces a root-cause hypothesis with a concrete patch plan.

---

## The Bug

**BUG-2041**: Background task jobs silently fail — dequeued by a worker, never written to DB,
no error raised, no retry triggered. Tasks stay stuck in a "processing" state.

The root cause (for context — the agents figure this out themselves): a race condition in the
task dequeue step. Under 8 concurrent workers, two threads occasionally pick up the same
task ID. The second one hits a DB unique constraint violation, catches the IntegrityError,
and then silently exits without updating the task status. The task never completes.

---

## How It Works

Five agents run in sequence:

```
Triage → Log Analyst → Reproduction → Fix Planner → Reviewer/Critic
```

| Agent | Role |
|-------|------|
| **Triage** | Parses the bug report → symptoms, environment, prioritized hypotheses |
| **Log Analyst** | Mines logs for stack traces, error signatures, double-pickup events |
| **Reproduction** | Generates a minimal stdlib-only repro script, runs it, confirms bug |
| **Fix Planner** | Proposes root cause + concrete patch plan + validation checklist |
| **Reviewer/Critic** | Challenges root cause validity, repro quality, and patch safety |

---

## Setup

```bash
# From the project root
pip install -r requirements.txt

cp .env.example .env
# Edit .env → OPENAI_API_KEY=your_key_here
```

---

## Running

```bash
# From the project root
python -m assessment_2.main
```

The YAML report is written to `assessment_2/outputs/report_<timestamp>.yaml`.
The repro script is written to `assessment_2/outputs/repro_test.py`.
The agent trace log is at `traces/assessment_2.jsonl`.

To specify a custom output path:
```bash
python -m assessment_2.main --output my_results/bug_report.yaml
```

---

## Running the Repro Script

The reproduction agent generates and runs a minimal script automatically.
You can also run it manually:

```bash
python assessment_2/outputs/repro_test.py
```

Expected output:
```
[REPRO CONFIRMED] X tasks stuck in 'processing' state
```

The script uses only Python stdlib — no Redis, no Flask, no external services needed.

---

## Inputs

| File | Description |
|------|-------------|
| `inputs/bug_report.md` | Bug report with symptoms, environment, and reproduction hints |
| `inputs/app.log` | Application log containing stack traces and noise |
| `inputs/sample_app/task_worker.py` | The buggy application code |

---

## Output Structure

The YAML report contains:
- `bug_summary` — symptoms, expected vs actual behavior, severity, environment
- `evidence` — extracted stack traces, error signatures, relevant log lines
- `repro` — path to repro script, run command, whether it succeeded
- `root_cause` — hypothesis with confidence + all hypotheses considered
- `patch_plan` — specific code changes with risk ratings
- `validation_plan` — tests to add and regression checks
- `open_questions` — things to confirm before shipping the fix
- `critic_review` — the reviewer's assessment and any flagged risks

---

## Trace Logs

`traces/assessment_2.jsonl` — one line per agent step and tool call.

```bash
cat traces/assessment_2.jsonl | python -m json.tool
```

Tool calls show both the arguments passed and the result returned, so you can
follow exactly what each agent saw at each step.
