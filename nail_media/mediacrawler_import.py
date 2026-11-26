"""Offline import of authorized MediaCrawler Douyin exports."""
import argparse
import json
import re
import sqlite3
import shutil
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image
from .image_processing import inspect_image
from .video_assets import ingest_video, SUPPORTED_EXTENSIONS, validate_source
from .catalog import Catalog


def import_batch(source, root, limit=100):
    source, root = Path(source).resolve(), Path(root).resolve()
    if not source.is_dir() or not 1 <= limit <= 1000:
        raise ValueError("Invalid source directory or limit")
    db_path = root / "catalog.sqlite3"
    Catalog(db_path)
    report = dict(posts=0, images=0, videos=0, duplicates=0, errors=[])
    with sqlite3.connect(db_path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS imported_posts (platform_id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS imported_post_assets (platform_id TEXT, sha256 TEXT, kind TEXT, PRIMARY KEY(platform_id,sha256,kind))")
        db.execute("CREATE TABLE IF NOT EXISTS crawler_assets (sha256 TEXT PRIMARY KEY, phash TEXT, payload TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS crawler_observations (platform TEXT, keyword TEXT, observed_sha TEXT, asset_sha TEXT, match_type TEXT, PRIMARY KEY(platform,keyword,observed_sha))")
    folders = {}
    for p in source.rglob("*"):
        if p.is_dir() and not p.is_symlink() and p.parent.name == "media" and p.resolve().is_relative_to(source):
            folders.setdefault(p.name, []).append(p)
    seen = set()
    for manifest in sorted(source.rglob("*.jsonl")):
        if not manifest.name.startswith("search_contents_") or not manifest.resolve().is_relative_to(source):
            continue
        with manifest.open(encoding="utf-8") as fp:
            for line in fp:
                if len(seen) >= limit:
                    break
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                    pid = str(row["aweme_id"])
                    if not re.fullmatch(r"[0-9]{1,25}", pid):
                        raise ValueError("Invalid post ID")
                    url = str(row["aweme_url"])
                    validate_source(url, "douyin")
                    if urlsplit(url).path.rstrip("/").split("/")[-1] != pid:
                        raise ValueError("Source ID mismatch")
                    if pid in seen:
                        continue
                    seen.add(pid)
                    title = str(row.get("title") or "")[:1000]
                    keyword = str(row.get("source_keyword") or "")[:200]
                    post = dict(platform="douyin", platform_id=pid, source_url=url,
                                title=title, description=str(row.get("desc") or "")[:10000],
                                keyword=keyword, post_type=str(row.get("aweme_type") or ""),
                                published_at=row.get("create_time"))
                    with sqlite3.connect(db_path) as db:
                        db.execute("INSERT OR REPLACE INTO imported_posts VALUES (?,?)", (pid,json.dumps(post,ensure_ascii=False)))
                    report["posts"] += 1
                    if not folders.get(pid):
                        report["errors"].append({"id":pid,"error":"missing_media_directory"})
                    for folder in folders.get(pid, []):
                        for path in sorted(folder.iterdir()):
                            if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(source):
                                continue
                            try:
                                if path.suffix.lower() in SUPPORTED_EXTENSIONS:
                                    result = ingest_video(path,url,platform="douyin",root=root,db_path=db_path,title=title,platform_id=pid)
                                    sha, kind = result["sha256"], "video"
                                else:
                                    info = inspect_image(path)
                                    sha, kind = info["sha256"], "image"
                                    with Image.open(path) as img:
                                        ext = {"JPEG":".jpg","PNG":".png","WEBP":".webp"}[img.format]
                                    target = root / "images" / (sha + ext)
                                    target.parent.mkdir(parents=True,exist_ok=True)
                                    if not target.exists():
                                        temp = target.with_suffix(".part")
                                        try:
                                            shutil.copyfile(path,temp)
                                            if inspect_image(temp)["sha256"] != sha:
                                                raise ValueError("Image changed during copy")
                                            temp.replace(target)
                                        finally:
                                            temp.unlink(missing_ok=True)
                                    with sqlite3.connect(db_path) as db:
                                        db.execute("INSERT OR IGNORE INTO crawler_assets VALUES (?,?,?)",(sha,info["phash"],json.dumps({**info,"path":str(target)})))
                                        db.execute("INSERT OR IGNORE INTO crawler_observations VALUES (?,?,?,?,?)",("douyin",keyword,sha,sha,"original"))
                                with sqlite3.connect(db_path) as db:
                                    inserted = db.execute("INSERT OR IGNORE INTO imported_post_assets VALUES (?,?,?)",(pid,sha,kind)).rowcount
                                report[kind+"s" if inserted else "duplicates"] += 1
                            except Exception as exc:
                                report["errors"].append({"id":pid,"file":path.name,"error":type(exc).__name__})
                except Exception as exc:
                    report["errors"].append({"error":type(exc).__name__})
    output = root / "reports" / "import-report.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--platform",choices=["douyin"],required=True)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--limit",type=int,default=100)
    p.add_argument("--confirm-authorized",action="store_true",required=True)
    a = p.parse_args()
    report = import_batch(a.input,a.root,a.limit)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 1 if report["errors"] or not report["posts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
