import argparse
import json
import sqlite3
from pathlib import Path
from .ollama_client import analyze
from .video_assets import sha256_file
from .tag_schema import TagsV2 as Tags
from pydantic import ValidationError

from .tag_router import route
import time

VERSION = "v2"

def run(root, *, model="qwen2.5vl:7b", limit=5, retry_failed=False, analyzer=analyze, fallback=None, representatives_only=False):
    if not 1 <= limit <= 1000:
        raise ValueError("Invalid limit")
    root = Path(root).resolve()
    path = root / "catalog.sqlite3"
    if not path.is_file():
        raise FileNotFoundError(path)
    started = time.monotonic()
    version = VERSION + ":routed:" + fallback if fallback else VERSION
    report = {"processed":0,"success":0,"review":0,"failed":0,"errors":[]}
    with sqlite3.connect(path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS image_tags (
            image_sha TEXT, model TEXT, version TEXT, status TEXT, payload TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(image_sha,model,version))""")
        if representatives_only and not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='image_clusters'").fetchone():
            raise ValueError("Run cluster_pipeline first")
        representative_filter = " AND EXISTS (SELECT 1 FROM image_clusters c WHERE c.representative_sha=a.sha256)" if representatives_only else ""
        rows = db.execute("""SELECT a.sha256,a.payload FROM crawler_assets a
            LEFT JOIN image_tags t ON t.image_sha=a.sha256 AND t.model=? AND t.version=?
            WHERE (t.image_sha IS NULL OR (? AND t.status='failed'))""" + representative_filter + " ORDER BY a.sha256 LIMIT ?",(model,version,int(retry_failed),limit)).fetchall()
        for sha,payload in rows:
            report["processed"] += 1
            try:
                filename = Path(json.loads(payload)["path"]).name
                image = root / "images" / filename
                if image.is_symlink() or sha256_file(image) != sha:
                    raise ValueError("Image integrity mismatch")
                if fallback:
                    status,result = route(image,model,fallback,analyzer)
                    if status == "failed":
                        report["errors"].append({"image_sha":sha,**result})
                else:
                    result = analyzer(image,model)
                    result = Tags.model_validate({k:v for k,v in result.items() if k!="need_review"}).result()
                    status = "review" if result["need_review"] else "success"
            except Exception as exc:
                status = "failed"
                result = {"error":type(exc).__name__}
                if isinstance(exc, ValidationError):
                    result["validation_errors"] = [{"loc":e["loc"],"type":e["type"]} for e in exc.errors(include_input=False,include_url=False,include_context=False)]
                report["errors"].append({"image_sha":sha,**result})
            with db:
                db.execute("""INSERT OR REPLACE INTO image_tags
                    (image_sha,model,version,status,payload) VALUES (?,?,?,?,?)""",
                    (sha,model,version,status,json.dumps(result,ensure_ascii=False)))
            report[status] += 1
    report["elapsed_seconds"] = round(time.monotonic()-started,3)
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path("runtime/media-library"))
    p.add_argument("--model",default="qwen2.5vl:7b")
    p.add_argument("--limit",type=int,default=5)
    p.add_argument("--retry-failed",action="store_true")
    p.add_argument("--fallback-model")
    p.add_argument("--representatives-only",action="store_true")
    a = p.parse_args()
    report = run(a.root,model=a.model,limit=a.limit,retry_failed=a.retry_failed,fallback=a.fallback_model,representatives_only=a.representatives_only)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(bool(report["failed"]))

if __name__ == "__main__":
    raise SystemExit(main())
