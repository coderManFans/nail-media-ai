"""Import operator-authorized platform exports without accessing platform accounts."""
import argparse
import json
from pathlib import Path
from .collectors import Media, platform_for
from .catalog import Catalog

def normalize(platform, rows):
    if platform not in {"baidu","xiaohongshu","douyin"}:
        raise ValueError("Unsupported platform")
    items, rejected = [], 0
    for row in rows:
        try:
            if platform == "baidu":
                source = row["source_url"]
                urls = [row["image_url"]]
                kind = "image"
            elif platform == "xiaohongshu":
                source = row.get("note_url") or row["source_url"]
                urls = row.get("image_list") or [source]
                if isinstance(urls,str):
                    urls = urls.split(",")
                kind = "image" if urls != [source] else "post"
            else:
                source = row.get("aweme_url") or row["source_url"]
                urls = [source]
                kind = "video"
            if platform_for(source) != platform:
                raise ValueError("Unexpected platform source")
            for url in urls:
                try:
                    item = Media(source,url.strip(),platform,kind,row.get("title") or row.get("desc") or "")
                    item.record()
                    items.append(item)
                except (ValueError,TypeError,AttributeError):
                    rejected += 1
        except (KeyError,ValueError,TypeError,AttributeError):
            rejected += 1
    return items,rejected

def main():
    p = argparse.ArgumentParser()
    p.add_argument("platform",choices=["baidu","xiaohongshu","douyin"])
    p.add_argument("file",type=Path)
    p.add_argument("--db",type=Path,default=Path("runtime/catalog.sqlite3"))
    p.add_argument("--confirm-authorized",action="store_true")
    a = p.parse_args()
    if not a.confirm_authorized:
        p.error("Confirm permission to retain exported metadata")
    raw = a.file.read_text(encoding="utf-8")
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()] if a.file.suffix == ".jsonl" else json.loads(raw)
    if not isinstance(rows,list):
        p.error("Expected JSON array or JSONL records")
    items,rejected = normalize(a.platform,rows)
    print(json.dumps({"accepted":len(items),"rejected":rejected,"inserted":Catalog(a.db).add(items)}))

if __name__ == "__main__":
    main()
