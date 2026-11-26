import sqlite3
import time
from pathlib import Path

class TaskStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS task_state (
                id TEXT PRIMARY KEY, status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_at REAL NOT NULL DEFAULT 0,
                updated_at REAL NOT NULL DEFAULT 0)""")

    def register(self, tasks):
        with sqlite3.connect(self.path) as db:
            db.executemany("INSERT OR IGNORE INTO task_state(id,status) VALUES (?, 'pending')",
                           [(t["id"],) for t in tasks])

    def claim(self, task_id, now=None):
        now = time.time() if now is None else now
        with sqlite3.connect(self.path) as db:
            cur = db.execute("""UPDATE task_state SET status='running',
                attempts=attempts+1, updated_at=? WHERE id=? AND
                status IN ('pending','retry_wait','success') AND next_at<=?""",
                (now,task_id,now))
            return cur.rowcount == 1

    def finish(self, task_id, status, interval_hours, now=None):
        now = time.time() if now is None else now
        with sqlite3.connect(self.path) as db:
            row = db.execute("SELECT attempts FROM task_state WHERE id=? AND status='running'",(task_id,)).fetchone()
            if not row:
                raise ValueError("Task not running")
            attempts = row[0]
            if status == "success":
                state, delay, attempts = "success", max(1,interval_hours)*3600, 0
            elif status in ("blocked","unconfigured","empty_or_filtered"):
                state, delay = status, 0
            elif attempts < 3:
                state, delay = "retry_wait", 60 * 2**(attempts-1)
            else:
                state, delay = "failed", 0
            db.execute("UPDATE task_state SET status=?,next_at=?,attempts=?,updated_at=? WHERE id=?",
                       (state,now+delay,attempts,now,task_id))

    def reset(self, task_id):
        with sqlite3.connect(self.path) as db:
            return db.execute("""UPDATE task_state SET status='pending',attempts=0,next_at=0
                WHERE id=? AND status IN ('failed','blocked','unconfigured','empty_or_filtered','running')""",
                (task_id,)).rowcount

    def rows(self):
        with sqlite3.connect(self.path) as db:
            db.row_factory = sqlite3.Row
            return [dict(r) for r in db.execute("SELECT * FROM task_state ORDER BY id")]
