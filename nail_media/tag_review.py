import argparse
import json
import sqlite3
import time
from pathlib import Path
from pydantic import ValidationError
from .ollama_client import analyze
from .tag_schema import TagsV2
from .video_assets import sha256_file

def eligible(status, payload):
    if status == "failed":
        return True
    if status != "review":
        return False
    return payload.get("content_type") in ("finished","unknown") or "content_type_conflict" in payload.get("review_reasons",[])

def run(root, primary, backup, *, limit=10, enqueue_only=False, retry_failed=False, analyzer=analyze):
    if primary == backup or not 1 <= limit <= 1000:
        raise ValueError("Invalid review configuration")
    root = Path(root).resolve()
    if not (root/"catalog.sqlite3").is_file():
        raise FileNotFoundError(root)
    report = {"queued":0,"processed":0,"review":0,"failed":0,"errors":[]}
    with sqlite3.connect(root/"catalog.sqlite3") as db:
        db.execute("""CREATE TABLE IF NOT EXISTS tag_review_queue (
            image_sha TEXT, primary_model TEXT, backup_model TEXT, state TEXT,
            payload TEXT, PRIMARY KEY(image_sha,primary_model,backup_model))""")
        for sha,status,raw in db.execute("SELECT image_sha,status,payload FROM image_tags WHERE model=? AND version='v2'",(primary,)):
            if eligible(status,json.loads(raw)):
                report["queued"] += db.execute("INSERT OR IGNORE INTO tag_review_queue VALUES (?,?,?,'pending','{}')",(sha,primary,backup)).rowcount
        db.commit()
        if enqueue_only:
            return report
        if retry_failed:
            with db:
                db.execute("UPDATE tag_review_queue SET state='pending' WHERE primary_model=? AND backup_model=? AND state='failed'",(primary,backup))
        rows = db.execute("""SELECT q.image_sha,a.payload,t.payload FROM tag_review_queue q
            JOIN crawler_assets a ON a.sha256=q.image_sha
            JOIN image_tags t ON t.image_sha=q.image_sha AND t.model=q.primary_model AND t.version='v2'
            WHERE q.primary_model=? AND q.backup_model=? AND q.state='pending'
            ORDER BY q.image_sha LIMIT ?""",(primary,backup,limit)).fetchall()
        for sha,asset,original in rows:
            start = time.monotonic()
            try:
                image = root/"images"/Path(json.loads(asset)["path"]).name
                if image.is_symlink() or sha256_file(image)!=sha:
                    raise ValueError("Image integrity mismatch")
                result = TagsV2.model_validate(analyzer(image,backup)).result()
                first = json.loads(original)
                differences = [k for k in ("content_type","nail_part","colors","styles","nail_shape","nail_length","finish","decorations")
                    if k in first and (set(first[k])!=set(result[k]) if isinstance(first[k],list) else first[k]!=result[k])]
                payload = {"candidate":result,"differences":differences,"seconds":round(time.monotonic()-start,3)}
                state = "review"
            except Exception as exc:
                payload = {"error":type(exc).__name__,"seconds":round(time.monotonic()-start,3)}
                if isinstance(exc,ValidationError):
                    payload["validation_errors"]=[{"loc":e["loc"],"type":e["type"]} for e in exc.errors(include_input=False,include_url=False,include_context=False)]
                report["errors"].append({"image_sha":sha,**payload})
                state = "failed"
            with db:
                db.execute("UPDATE tag_review_queue SET state=?,payload=? WHERE image_sha=? AND primary_model=? AND backup_model=?",(state,json.dumps(payload,ensure_ascii=False),sha,primary,backup))
            report["processed"] += 1
            report[state] += 1
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default="runtime/media-library")
    p.add_argument("--model",default="qwen2.5vl:7b")
    p.add_argument("--fallback-model",default="qwen3.5:9b")
    p.add_argument("--limit",type=int,default=10)
    p.add_argument("--enqueue-only",action="store_true")
    p.add_argument("--retry-failed",action="store_true")
    a=p.parse_args()
    result=run(a.root,a.model,a.fallback_model,limit=a.limit,enqueue_only=a.enqueue_only,retry_failed=a.retry_failed)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return int(bool(result["failed"]))

if __name__=="__main__":
    raise SystemExit(main())
