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
                    sources = []
                    for (source_payload,) in db.execute(
                        "SELECT payload FROM video_sources WHERE asset_sha=? ORDER BY media_id",
                        (sha,),
                    ):
                        source = json.loads(source_payload)
                        if "video_keywords" in tables:
                            source["keywords"] = [
                                row[0] for row in db.execute(
                                    """SELECT keyword FROM video_keywords
                                    WHERE platform=? AND platform_id=? ORDER BY keyword""",
                                    (source.get("platform"), source.get("platform_id")),
                                )
                            ]
                        sources.append(source)
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
            if {"imported_posts", "imported_post_assets"} <= tables:
                for key, payload in db.execute("SELECT platform_id,payload FROM imported_posts ORDER BY platform_id"):
                    post = json.loads(payload)
                    record = {k: post.get(k) for k in (
                        "platform", "platform_id", "source_url", "title",
                        "keyword", "post_type", "published_at")}
                    record.update(id=post["platform"] + ":" + post["platform_id"],
                                  record_type="post", license_status="unknown")
                    record["assets"] = [
                        {"sha256": sha, "kind": kind}
                        for sha, kind in db.execute(
                            "SELECT sha256,kind FROM imported_post_assets WHERE platform_id=? ORDER BY kind,sha256",
                            (key,))
                    ]
                    rows.append((json.dumps(record, ensure_ascii=False),))
            specs = [
                ("manual_tags","manual_tag",("image_sha",),()),
                ("image_tags","image_tag",("image_sha","model","version"),("status",)),
                ("image_recommendations","image_recommendation",("image_sha","model","tag_version","rule_version"),()),
                ("video_frames","video_frame",("video_sha","frame_index","interval"),("image_sha",)),
                ("image_cluster_members","image_cluster_member",("image_sha",),("cluster_id",)),
            ]
            for table,kind,keys,fields in specs:
                if table not in tables:
                    continue
                columns = keys + fields
                for row in db.execute("SELECT "+",".join(columns)+",payload FROM "+table+" ORDER BY "+",".join(keys)):
                    record = dict(zip(columns,row[:-1]))
                    record.update(id=json.dumps(row[:len(keys)],ensure_ascii=False,separators=(",",":")),record_type=kind)
                    payload = json.loads(row[-1])
                    allowed = {
                        "manual_tag": ("is_nail_art","content_type","nail_part","design_visibility","colors","styles","nail_shape","nail_length","decorations","finish","confidence","need_review","recommendation_eligible"),
                        "image_tag": ("is_nail_art","content_type","nail_part","design_visibility","colors","styles","nail_shape","nail_length","decorations","finish","confidence","need_review","recommendation_eligible","review_reasons","selected_model","model_differences"),
                        "image_recommendation": ("scenes","seasons","evidence"),
                        "video_frame": ("estimated_seconds","quality"),
                        "image_cluster_member": ("phash_distance","dhash_distance","color_distance","matched"),
                    }[kind]
                    record["data"] = {k:payload[k] for k in allowed if k in payload}
                    rows.append((json.dumps(record,ensure_ascii=False),))
        temp = path.with_suffix(".tmp")
        temp.write_text("".join(r[0] + "\n" for r in rows), encoding="utf-8")
        temp.replace(path)
        return len(rows)
