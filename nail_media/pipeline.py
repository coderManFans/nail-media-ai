import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .download import download_image

def run_task(task, providers, catalog, client, root, approved_urls=()):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    report = {"id":task["id"],"started":datetime.now(timezone.utc).isoformat(),"found":0,"inserted":0,"downloaded":0,"errors":[]}
    try:
        provider = providers[task["platform"]]
        items = provider.search(task["keyword"],task["limit"])[:task["limit"]]
        report["found"] = len(items)
        report["inserted"] = catalog.add(items)
        with sqlite3.connect(catalog.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS image_files (media_id TEXT PRIMARY KEY, sha256 TEXT, phash TEXT, payload TEXT)")
            for item in items:
                if item.media_type != "image" or item.media_url not in approved_urls:
                    continue
                try:
                    result = download_image(client,item.media_url,root/"images",authorized=True)
                    db.execute("INSERT OR REPLACE INTO image_files VALUES (?,?,?,?)",(item.record()["id"],result["sha256"],result["phash"],json.dumps(result)))
                    report["downloaded"] += 1
                except Exception as exc:
                    report["errors"].append(type(exc).__name__)
        report["status"] = "partial" if report["errors"] else "success"
    except KeyError:
        report["status"] = "unconfigured"
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append(type(exc).__name__)
    report["finished"] = datetime.now(timezone.utc).isoformat()
    with (root/"history.jsonl").open("a",encoding="utf-8") as out:
        out.write(json.dumps(report)+"\n")
    return report
