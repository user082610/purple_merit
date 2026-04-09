# Bug Report — Task Worker Silent Failure

**ID:** BUG-2041  
**Filed by:** Priya Menon (Backend Team)  
**Date:** 2026-04-07  
**Severity:** High  
**Status:** Open

---

## Title

Background task jobs sometimes don't complete — no error thrown, no retry triggered

## Description

We've been seeing intermittent failures in the task processing pipeline over the past week.
Jobs are being picked up from the queue (confirmed via queue depth metrics going down), but
the result never gets written. No exception is raised. No dead-letter queue entry. It just
disappears silently.

This is especially bad for payment confirmation jobs — the user sees a "processing" spinner
indefinitely. We've had maybe 15-20 confirmed cases over the last 3 days, but suspect the
actual number is higher since we only catch it when users report it.

## Expected Behavior

Every job dequeued by a worker must either:
- Complete successfully and write its result to the DB, OR
- Fail with an exception and be re-queued via the retry handler

Silent completion without a result written should never happen.

## Actual Behavior

Jobs are dequeued, the worker logs "picked up task [id]", and then... nothing.
No result. No error. No retry. The task stays in a "processing" limbo state
until the stale-task cleanup job runs 6 hours later and marks it as failed.

## Environment

- Python 3.10.12
- Flask 3.0.1
- Redis 7.2 (task queue)
- Workers run as threads (ThreadPoolExecutor, max_workers=8)
- Deployment: Docker on AWS ECS, 3 worker containers
- OS: Linux (Alpine 3.18)

## Reproduction Hints

Hard to reproduce deterministically. Seems to happen more often under load (>50 concurrent
users). One engineer managed to trigger it by running 100 simultaneous requests against
staging but couldn't pin down the exact sequence.

The bug was NOT present before the worker pool was scaled from 4 → 8 threads on 2026-04-01.
That's the most obvious correlation we have.

## Logs Reference

See `app.log` — search for "picked up task" entries that don't have a corresponding
"task complete" or "task failed" within the next 30 seconds.

## What We've Already Tried

- Added more logging around the dequeue step → confirms jobs are being picked up
- Checked Redis TTL — keys aren't expiring prematurely  
- Verified DB connection pool — no obvious exhaustion
- Restarted containers — doesn't help, happens again after 30-60 minutes

## Suspected Area

The `task_worker.py` dequeue → execute → write result flow. Possibly a race condition
between two workers picking up the same task ID. Haven't confirmed this yet.
