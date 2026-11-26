import argparse
import json
import sqlite3
from pathlib import Path
from .image_features import features, compare, quality
from .similarity_index import BKTree
from .video_assets import sha256_file

VERSION = "v1"

def cluster(items):
    tree = BKTree()
    groups = {}
    for sha,f in sorted(items.items(),key=lambda pair:(quality(pair[1]),pair[0]),reverse=True):
        candidates = []
        for representative in tree.search(f["phash"]):
            score = compare(f,items[representative])
            if score["matched"]:
                candidates.append((score["color_distance"],score["phash_distance"],representative,score))
        if candidates:
            _,_,rep,score = min(candidates)
            groups[rep].append((sha,score))
        else:
            tree.add(f["phash"],sha)
            groups[sha] = [(sha,compare(f,f))]
    return groups

def run(root):
    root = Path(root).resolve()
    path = root/"catalog.sqlite3"
    if not path.is_file():
        raise FileNotFoundError(path)
    errors = []
    items = {}
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS image_features (image_sha TEXT, version TEXT, payload TEXT, PRIMARY KEY(image_sha,version))")
        db.execute("CREATE TABLE IF NOT EXISTS image_clusters (cluster_id TEXT PRIMARY KEY, representative_sha TEXT, version TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS image_cluster_members (image_sha TEXT PRIMARY KEY, cluster_id TEXT, payload TEXT)")
        rows = db.execute("SELECT sha256,payload FROM crawler_assets ORDER BY sha256").fetchall()
        for sha,payload in rows:
            try:
                image = root/"images"/Path(json.loads(payload)["path"]).name
                if image.is_symlink() or not image.is_file():
                    raise ValueError("Missing image")
                cached = db.execute("SELECT payload FROM image_features WHERE image_sha=? AND version=?",(sha,VERSION)).fetchone()
                if cached:
                    f = json.loads(cached[0])
                else:
                    if sha256_file(image) != sha:
                        raise ValueError("Image integrity mismatch")
                    f = features(image)
                    db.execute("INSERT INTO image_features VALUES (?,?,?)",(sha,VERSION,json.dumps(f)))
                items[sha] = f
            except Exception as exc:
                errors.append({"image_sha":sha,"error":type(exc).__name__})
        groups = cluster(items)
        with db:
            db.execute("DELETE FROM image_cluster_members")
            db.execute("DELETE FROM image_clusters")
            for rep,members in groups.items():
                db.execute("INSERT INTO image_clusters VALUES (?,?,?)",(rep,rep,VERSION))
                db.executemany("INSERT INTO image_cluster_members VALUES (?,?,?)",[(sha,rep,json.dumps(score)) for sha,score in members])
    return {"images":len(items),"clusters":len(groups),"similar_images":len(items)-len(groups),
            "multi_image_clusters":sum(len(m)>1 for m in groups.values()),"errors":errors}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path("runtime/media-library"))
    a = p.parse_args()
    result = run(a.root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return int(bool(result["errors"]))

if __name__ == "__main__":
    raise SystemExit(main())
