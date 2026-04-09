# Purple Merit Technologies — AI/ML Engineer Assessment

Submission for the AI/ML Engineer assessment (April 2026). Both assessments are implemented.

---

## What's Here

| Directory | Assessment |
|-----------|------------|
| `assessment_1/` | War Room Launch Decision System |
| `assessment_2/` | Automated Bug Investigation System |
| `shared/` | Common utilities (LLM factory, tracer, console) |
| `traces/` | Agent step logs (generated at runtime) |

---

## Architecture Overview

Both assessments use the same pattern:

- **LangGraph** for orchestration — each agent is a graph node, state flows through explicit edges
- **OpenAI GPT-4o** as the LLM (configurable via `.env`)
- **Pydantic / TypedDict** for structured state between agents
- **Rich** for readable CLI output
- **JSONL trace logs** so every agent step and tool call is inspectable

I went with LangGraph over CrewAI or AutoGen because I wanted an explicit,
deterministic state machine where I control exactly what each agent sees and when.
The graph structure also makes it easy to add conditional edges or loops later
(e.g., looping back to re-analyze if the critic flags a major issue).

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up your API key
cp .env.example .env
# → Edit .env and set OPENAI_API_KEY=your_key_here

# 3. Run Assessment 1 (War Room)
python -m assessment_1.main

# 4. Run Assessment 2 (Bug Investigation)
python -m assessment_2.main
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | — | Your OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o` | Override the model (e.g. `gpt-4-turbo`) |

---

## Outputs

| File | Description |
|------|-------------|
| `assessment_1/outputs/decision_*.json` | War room structured decision |
| `assessment_2/outputs/report_*.yaml` | Bug investigation report |
| `assessment_2/outputs/repro_test.py` | Generated minimal repro script |
| `traces/assessment_1.jsonl` | Assessment 1 agent trace |
| `traces/assessment_2.jsonl` | Assessment 2 agent trace |

---

## If I Had More Time

- **Assessment 1**: Add a conditional loop so the Critic can send agents back for
  a second pass when it flags a high-confidence gap (not just append notes).
- **Assessment 2**: Add a Repo Navigator agent that actually reads the sample app
  code and proposes a diff-level patch, not just a description.
- **Both**: Add async agent execution for steps that don't depend on each other
  (e.g., run the PM and Marketing agents in parallel once the Analyst finishes).
- **Testing**: Add unit tests for all the tool functions — they're pure functions
  so they're trivial to test, I just ran out of time.

---

*Samyuktha Nagaraj | AI/ML Engineer Assessment | April 2026*
