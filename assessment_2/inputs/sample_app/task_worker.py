"""
Minimal task worker — this is the buggy version.

The bug: dequeue uses Redis LPOP without any atomic locking.
Under concurrent workers, two threads can both call LPOP in the same
millisecond window on a list-based queue and get the same task.
(Redis LPOP is atomic for single operations, but our queue uses a separate
"mark as processing" step which is NOT atomic — that's where the race lives.)
"""

import time
import threading
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import redis


# Shared state — in a real app this would be per-request DB sessions,
# not a module-level connection. That's actually fine here since SQLite
# in WAL mode handles concurrent readers, but the task dequeue is still racy.
DB_PATH = "tasks.db"
QUEUE_KEY = "task_queue"

r = redis.Redis(host="localhost", port=6379, decode_responses=True)
db_lock = threading.Lock()  # added too late — doesn't cover the dequeue step


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS task_results (
            task_id TEXT PRIMARY KEY,
            result TEXT NOT NULL,
            completed_at REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()


def enqueue_task(task_id: str, payload: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT OR IGNORE INTO tasks (task_id, payload, status) VALUES (?, ?, 'pending')", (task_id, payload))
    conn.commit()
    conn.close()
    # Push to Redis queue
    r.rpush(QUEUE_KEY, task_id)


def dequeue_task() -> str | None:
    """
    THE BUGGY DEQUEUE.

    LPOP is atomic, so two workers won't get the same value in the same call.
    BUT — we have a separate "mark as processing" UPDATE below that isn't
    part of the same atomic operation. Under high concurrency with the
    Redis queue empty but the DB still showing 'pending', a second worker
    can slip in between LPOP and the status update.

    Actually the real race is subtler: we pushed the same task_id to the
    queue twice in stress testing (bug in enqueue_task when called concurrently
    without a lock), so LPOP returns duplicate task_ids to separate workers.
    """
    task_id = r.lpop(QUEUE_KEY)
    if not task_id:
        return None

    # This UPDATE is not atomic with the LPOP above.
    # Two workers can both LPOP the same task_id if it was enqueued twice.
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE tasks SET status='processing' WHERE task_id=?", (task_id,))
    conn.commit()
    conn.close()

    return task_id


def process_task(task_id: str) -> dict:
    """Simulate doing work — in practice this calls an external API."""
    time.sleep(0.05)  # pretend we're doing something
    return {"status": "confirmed", "task_id": task_id, "ts": time.time()}


def write_result(task_id: str, result: dict):
    """
    Writes result to DB. Swallows IntegrityError because we assumed it meant
    "another worker already handled it" — but that assumption is wrong.
    When the second worker hits the IntegrityError, it exits WITHOUT updating
    the task status to 'complete'. The task stays as 'processing' forever.
    """
    conn = sqlite3.connect(DB_PATH)
    try:
        with db_lock:
            conn.execute(
                "INSERT INTO task_results (task_id, result, completed_at) VALUES (?, ?, ?)",
                (task_id, str(result), time.time()),
            )
            conn.execute("UPDATE tasks SET status='complete' WHERE task_id=?", (task_id,))
            conn.commit()
    except sqlite3.IntegrityError:
        # BUG: we swallow this and never update status to 'complete'
        # The task stays as 'processing' indefinitely
        print(f"[WARNING] IntegrityError swallowed for {task_id} — assuming already handled")
    finally:
        conn.close()


def worker_loop(worker_id: int):
    print(f"[worker-{worker_id}] starting")
    for _ in range(20):
        task_id = dequeue_task()
        if task_id:
            print(f"[worker-{worker_id}] picked up task {task_id}")
            result = process_task(task_id)
            write_result(task_id, result)
        time.sleep(0.01)


def run_workers(n_workers: int = 8):
    with ThreadPoolExecutor(max_workers=n_workers) as pool:
        futures = [pool.submit(worker_loop, i + 1) for i in range(n_workers)]
        for f in futures:
            f.result()


if __name__ == "__main__":
    init_db()

    # Seed some tasks — note: enqueue_task called concurrently without a lock
    # can push duplicate task IDs to the Redis list. That's the second bug.
    for i in range(10):
        enqueue_task(f"task-{1000 + i}", f'{{"type": "payment_confirmation", "order_id": {1000+i}}}')

    print("Running worker pool...")
    run_workers(n_workers=8)

    # Check for tasks stuck in 'processing' state
    conn = sqlite3.connect(DB_PATH)
    stuck = conn.execute("SELECT task_id, status FROM tasks WHERE status != 'complete'").fetchall()
    conn.close()

    if stuck:
        print(f"\n[!] {len(stuck)} tasks never completed:")
        for row in stuck:
            print(f"    {row[0]} → {row[1]}")
    else:
        print("\n[OK] All tasks completed.")
