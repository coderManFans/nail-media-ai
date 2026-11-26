"""Read-only counts of catalog records and platform associations."""
import argparse
import json
import sqlite3
from pathlib import Path


def statistics(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as db:
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts = {}
        for table in ("media","crawler_assets","video_assets","imported_posts","imported_post_assets"):
            counts[table] = db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] if table in tables else 0
        platforms = {}
        for platform in ("baidu","xiaohongshu","douyin","tiktok"):
            item = {"images":0,"videos":0,"posts":0}
            if "crawler_observations" in tables:
                item["images"] = db.execute("SELECT COUNT(DISTINCT asset_sha) FROM crawler_observations WHERE platform=?", (platform,)).fetchone()[0]
            if "video_sources" in tables:
                item["videos"] = db.execute("SELECT COUNT(DISTINCT asset_sha) FROM video_sources WHERE platform=?", (platform,)).fetchone()[0]
            if "imported_posts" in tables:
                item["posts"] = db.execute("SELECT COUNT(*) FROM imported_posts WHERE json_extract(payload,'$.platform')=?", (platform,)).fetchone()[0]
            platforms[platform] = item
        return {"counts":counts,"platforms":platforms}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db",type=Path,default=Path("runtime/media-library/catalog.sqlite3"))
    a = p.parse_args()
    print(json.dumps(statistics(a.db),ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
