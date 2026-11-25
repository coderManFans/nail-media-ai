import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .download import download_image
from .image_processing import similar
from .pagination import collect_pages

def run_task(task, providers, catalog, client, root, approved_urls=(), allowed_hosts=('upload.wikimedia.org',)):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    report = {"id":task["id"],"started":datetime.now(timezone.utc).isoformat(),"found":0,"inserted":0,"downloaded":0,"duplicates":0,"near_duplicates":0,"not_approved":0,"errors":[]}
    try:
        if task["platform"] not in providers:
            report["status"] = "unconfigured"
            raise LookupError("Provider unavailable")
        provider = providers[task["platform"]]
        limit = min(20, task["limit"])
        if hasattr(provider,"search_page"):
            items = collect_pages(lambda page: provider.search_page(task["keyword"],limit,page),limit=limit,max_pages=task.get("max_pages",3))
        else:
            items = provider.search(task["keyword"],limit)[:limit]
        report["found"] = len(items)
        report["inserted"] = catalog.add(items)
        with sqlite3.connect(catalog.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS image_files (media_id TEXT PRIMARY KEY, sha256 TEXT, phash TEXT, payload TEXT)")
            for item in items:
                if item.media_type != "image":
                    continue
                if item.media_url not in approved_urls:
                    report["not_approved"] += 1
                    continue
                try:
                    if db.execute("SELECT 1 FROM image_files WHERE media_id=?", (item.record()["id"],)).fetchone():
                        report["duplicates"] += 1
                        continue
                    result = download_image(client,item.media_url,root/"images",authorized=True,allowed_hosts=allowed_hosts)
                    hashes = db.execute("SELECT sha256, phash FROM image_files").fetchall()
                    if any(sha == result["sha256"] for sha, phash in hashes):
                        report["duplicates"] += 1
                        continue
                    elif any(similar(phash,result["phash"]) for sha, phash in hashes):
                        report["near_duplicates"] += 1
                        Path(result["path"]).unlink(missing_ok=True)
                        continue
                    db.execute("INSERT OR REPLACE INTO image_files VALUES (?,?,?,?)",(item.record()["id"],result["sha256"],result["phash"],json.dumps(result)))
                    report["downloaded"] += 1
                except Exception as exc:
                    report["errors"].append(type(exc).__name__)
        report["status"] = "partial" if report["errors"] else ("success" if items else "empty_or_filtered")
    except PermissionError:
        report["status"] = "blocked"
        report["errors"].append("PermissionError")
    except LookupError as exc:
        if report.get("status") != "unconfigured":
            report["status"] = "failed"
            report["errors"].append(type(exc).__name__)
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append(type(exc).__name__)
    report["finished"] = datetime.now(timezone.utc).isoformat()
    with (root/"history.jsonl").open("a",encoding="utf-8") as out:
        out.write(json.dumps(report)+"\n")
    return report
