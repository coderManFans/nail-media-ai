import json
import shutil
import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
from .image_processing import inspect_image, similar
from PIL import Image

EXTENSIONS = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}

def asset_path(images, sha):
    for ext in ('', *EXTENSIONS.values()):
        path = images / (sha + ext)
        if path.is_file():
            return path
    return None

def crawl_baidu(keyword, limit, directory):
    from icrawler.builtin import BaiduImageCrawler
    crawler = BaiduImageCrawler(feeder_threads=1, parser_threads=1,
        downloader_threads=1, storage={"root_dir":str(directory)})
    crawler.crawl(keyword=keyword,max_num=limit,min_size=(200,200))

def run_icrawler_task(task, catalog, root, crawl=crawl_baidu):
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    images=root/"images"
    images.mkdir(exist_ok=True)
    report={"id":task["id"],"engine":"icrawler","started":datetime.now(timezone.utc).isoformat(),
        "found":0,"inserted":0,"downloaded":0,"duplicates":0,"near_duplicates":0,"errors":[]}
    try:
        limit=int(task["limit"])
        if not 1<=limit<=20:
            raise ValueError("limit must be 1..20")
        with TemporaryDirectory(dir=root) as tmp:
            crawl(task["keyword"],limit,Path(tmp))
            with sqlite3.connect(catalog.path) as db:
                db.execute("CREATE TABLE IF NOT EXISTS crawler_assets (sha256 TEXT PRIMARY KEY, phash TEXT NOT NULL, payload TEXT NOT NULL)")
                db.execute("CREATE TABLE IF NOT EXISTS crawler_observations (platform TEXT, keyword TEXT, observed_sha TEXT, asset_sha TEXT, match_type TEXT, PRIMARY KEY(platform,keyword,observed_sha))")
                for path in sorted(Path(tmp).iterdir())[:limit]:
                    if not path.is_file(): continue
                    report["found"]+=1
                    try:
                        info=inspect_image(path)
                        sha=info["sha256"]
                        with Image.open(path) as im:
                            ext=EXTENSIONS[im.format]
                        target=images/(sha+ext)
                        rows=db.execute("SELECT sha256,phash FROM crawler_assets").fetchall()
                        exact=next((s for s,p in rows if s==sha and asset_path(images,s) is not None),None)
                        near=next((s for s,p in rows if asset_path(images,s) is not None and similar(p,info["phash"])),None) if not exact else None
                        if exact:
                            asset,match=exact,"exact"
                            report["duplicates"]+=1
                        elif near:
                            asset,match=near,"near"
                            report["near_duplicates"]+=1
                        else:
                            asset,match=sha,"original"
                            shutil.copyfile(path,target)
                            db.execute("INSERT OR REPLACE INTO crawler_assets VALUES (?,?,?)",(sha,info["phash"],json.dumps({**info,"path":str(target)})))
                            report["downloaded"]+=1
                        cur=db.execute("INSERT OR IGNORE INTO crawler_observations VALUES (?,?,?,?,?)",("baidu",task["keyword"],sha,asset,match))
                        report["inserted"]+=cur.rowcount
                    except Exception as exc:
                        report["errors"].append(type(exc).__name__)
        report["status"]="partial" if report["errors"] else ("success" if report["found"] else "empty_or_filtered")
    except Exception as exc:
        report["status"]="failed"
        report["errors"].append(type(exc).__name__)
    report["finished"]=datetime.now(timezone.utc).isoformat()
    with (root/"history.jsonl").open("a",encoding="utf-8") as out:
        out.write(json.dumps(report,ensure_ascii=False)+"\n")
    return report
