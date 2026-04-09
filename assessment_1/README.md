# Assessment 1 — Product Launch War Room

A multi-agent system that simulates a cross-functional war room during a feature launch.
Given a 14-day metric dashboard and user feedback dataset, a crew of specialized agents
deliberate and produce a structured launch decision: **Proceed**, **Pause**, or **Roll Back**.

---

## How It Works

Five agents run in sequence, each handing off to the next:

```
Data Analyst → PM → Marketing → Risk/Critic → Coordinator
```

| Agent | Role |
|-------|------|
| **Data Analyst** | Detects anomalies and trends in the 14-day metrics |
| **Product Manager** | Evaluates findings against launch success criteria |
| **Marketing/Comms** | Assesses sentiment trajectory and drafts messaging |
| **Risk/Critic** | Challenges all three — finds gaps, flags second-order risks |
| **Coordinator** | Synthesizes everything into a final structured decision |

The orchestration uses [LangGraph](https://github.com/langchain-ai/langgraph) — a state machine
graph where each agent is a node and state flows through explicitly defined edges. I picked it
over CrewAI because I wanted deterministic, inspectable handoffs rather than autonomous back-and-forth.

---

## Setup

```bash
# From the project root
pip install -r requirements.txt

# Copy and fill in your API key
cp .env.example .env
# Edit .env → set OPENAI_API_KEY=your_key_here
```

---

## Running

```bash
# From the project root
python -m assessment_1.main
```

The output JSON is written to `assessment_1/outputs/decision_<timestamp>.json`.
The agent trace log is written to `traces/assessment_1.jsonl`.

To specify a custom output path:
```bash
python -m assessment_1.main --output my_results/launch_decision.json
```

---

## Mock Dataset

The mock data in `data/` tells a realistic story:

- **Metrics** (`metrics.json`): 14 days of time series. Looks healthy in the first 3 days,
  then crash rate, API latency, and payment failures start a slow creep from Day 4 onward.
  By Day 14, payment failure rate is at 11.9% vs 2.9% at launch.

- **User Feedback** (`user_feedback.json`): 40 entries spanning the 14 days. Early feedback
  is positive. From Day 7 onward it shifts to frustration, then outright complaints about
  checkout timing out and the app crashing mid-payment.

- **Release Notes** (`release_notes.md`): Documents the feature change and, importantly,
  flags that a known payment gateway timeout issue under load was not fully resolved before launch.

---

## Output Structure

```json
{
  "decision": "ROLL_BACK | PAUSE | PROCEED",
  "rationale": "...",
  "risk_register": [...],
  "action_plan": [...],
  "communication_plan": { "internal": "...", "external": "..." },
  "confidence_score": 0.87,
  "confidence_factors": [...],
  "agent_reports": { "data_analyst": "...", ... }
}
```

---

## Trace Logs

`traces/assessment_1.jsonl` — one JSON line per agent step. Each line has:
- `ts` — UTC timestamp
- `agent` — which agent produced this entry
- `step` — what stage (e.g. `analysis_complete`, `decision_made`)
- `data` — payload (key metrics, counts, etc.)

To follow the trace:
```bash
cat traces/assessment_1.jsonl | python -m json.tool
```
