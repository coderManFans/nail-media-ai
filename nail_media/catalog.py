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
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if {"crawler_assets","crawler_observations"} <= tables:
                for sha, phash, payload in db.execute("SELECT sha256,phash,payload FROM crawler_assets ORDER BY sha256"):
                    info = json.loads(payload)
                    observations = [{"platform":p,"keyword":k,"observed_sha":s,"match_type":m} for p,k,s,m in db.execute("SELECT platform,keyword,observed_sha,match_type FROM crawler_observations WHERE asset_sha=? ORDER BY platform,keyword,observed_sha",(sha,))]
                    record = {"id":sha,"record_type":"image_asset","sha256":sha,"phash":phash,"width":info["width"],"height":info["height"],"filename":Path(info["path"]).name,"license_status":"unknown","observations":observations}
                    rows.append((json.dumps(record,ensure_ascii=False),))
            if {"video_assets", "video_sources"} <= tables:
                for sha, payload in db.execute("SELECT sha256,payload FROM video_assets ORDER BY sha256"):
                    asset = json.loads(payload)
                    sources = [
                        json.loads(source_payload)
                        for (source_payload,) in db.execute(
                            "SELECT payload FROM video_sources WHERE asset_sha=? ORDER BY media_id",
                            (sha,),
                        )
                    ]
                    record = {
                        "id": sha, "record_type": "video_asset",
                        "sha256": sha, "filename": asset["filename"],
                        "width": asset["width"], "height": asset["height"],
                        "size_bytes": asset["size_bytes"],
                        "duration_seconds": asset["duration_seconds"],
                        "license_status": asset.get("license_status", "unknown"),
                        "sources": sources,
                    }
                    rows.append((json.dumps(record, ensure_ascii=False),))
        temp = path.with_suffix(".tmp")
        temp.write_text("".join(r[0] + "\n" for r in rows), encoding="utf-8")
        temp.replace(path)
        return len(rows)
