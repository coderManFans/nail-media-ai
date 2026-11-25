import json
import sqlite3
from pathlib import Path

class Catalog:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        with sqlite3.connect(path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS media (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def add(self, items):
        rows = [item.record() for item in items]
        with sqlite3.connect(self.path) as db:
            before = db.total_changes
            db.executemany("INSERT OR IGNORE INTO media VALUES (?, ?)", [(r["id"], json.dumps(r, ensure_ascii=False)) for r in rows])
            return db.total_changes - before

    def export(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as db:
            rows = db.execute("SELECT payload FROM media ORDER BY id").fetchall()
        temp = path.with_suffix(".tmp")
        temp.write_text("".join(r[0] + "\n" for r in rows), encoding="utf-8")
        temp.replace(path)
        return len(rows)
