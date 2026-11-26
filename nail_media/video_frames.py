"""Extract and catalog representative video frames using FFmpeg."""
import argparse
import json
import math
import shutil
import sqlite3
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image, ImageStat, ImageFilter
from .image_processing import inspect_image, similar
from .video_assets import sha256_file


def quality(path):
    with Image.open(path) as image:
        gray = image.convert("L")
        gray.thumbnail((512,512))
        stat = ImageStat.Stat(gray)
        edges = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))
        return {"brightness":stat.mean[0],"contrast":stat.stddev[0],
                "edge_score":edges.stddev[0]}


def extract(path, directory, interval, maximum):
    subprocess.run(["ffmpeg","-nostdin","-v","error","-i",str(path),
                    "-vf",f"fps=1/{interval}:start_time=0:round=up",
                    "-frames:v",str(maximum),"-q:v","3",
                    str(directory / "%06d.jpg")],check=True,timeout=300)
    return sorted(directory.glob("*.jpg"))


def process(root, *, interval=2, maximum=30, limit=20, extractor=extract):
    if not math.isfinite(interval) or not 0.5 <= interval <= 60 or not 1 <= maximum <= 100 or not 1 <= limit <= 1000:
        raise ValueError("Invalid extraction limits")
    root = Path(root).resolve()
    dbpath = root / "catalog.sqlite3"
    if not dbpath.is_file():
        raise FileNotFoundError(dbpath)
    images = root / "images"
    images.mkdir(exist_ok=True)
    report = dict(videos=0,frames=0,filtered=0,duplicates=0,skipped=0,errors=[])
    with sqlite3.connect(dbpath) as db:
        db.execute("CREATE TABLE IF NOT EXISTS video_frames (video_sha TEXT, frame_index INTEGER, interval REAL, image_sha TEXT, payload TEXT, PRIMARY KEY(video_sha,frame_index,interval))")
        db.execute("CREATE TABLE IF NOT EXISTS frame_runs (video_sha TEXT, interval REAL, maximum INTEGER, PRIMARY KEY(video_sha,interval,maximum))")
        db.execute("CREATE TABLE IF NOT EXISTS crawler_assets (sha256 TEXT PRIMARY KEY, phash TEXT, payload TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS crawler_observations (platform TEXT, keyword TEXT, observed_sha TEXT, asset_sha TEXT, match_type TEXT, PRIMARY KEY(platform,keyword,observed_sha))")
        tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "video_assets" not in tables:
            return report
        rows = db.execute("SELECT sha256,payload FROM video_assets ORDER BY sha256").fetchall()
        for sha,payload in rows:
            if report["videos"] >= limit:
                break
            if db.execute("SELECT 1 FROM frame_runs WHERE video_sha=? AND interval=? AND maximum=?",(sha,interval,maximum)).fetchone():
                report["skipped"] += 1
                continue
            report["videos"] += 1
            try:
                asset = json.loads(payload)
                filename = asset["filename"]
                if Path(filename).name != filename:
                    raise ValueError("Invalid filename")
                video = root / "videos" / filename
                if video.is_symlink() or sha256_file(video) != sha:
                    raise ValueError("Video integrity mismatch")
                with TemporaryDirectory(dir=root) as tmp:
                    frames = extractor(video,Path(tmp),interval,maximum)
                    hashes = []
                    with db:
                        for index,frame in enumerate(frames[:maximum]):
                            try:
                                info = inspect_image(frame)
                                q = quality(frame)
                            except (ValueError,OSError):
                                report["filtered"] += 1
                                continue
                            if not 12 <= q["brightness"] <= 245 or q["contrast"] < 8 or q["edge_score"] < 8:
                                report["filtered"] += 1
                                continue
                            if any(similar(h,info["phash"]) for h in hashes):
                                report["duplicates"] += 1
                                continue
                            hashes.append(info["phash"])
                            image_sha = info["sha256"]
                            target = images / (image_sha + ".jpg")
                            if not target.exists():
                                temp = target.with_suffix(".part")
                                try:
                                    shutil.copyfile(frame,temp)
                                    if sha256_file(temp) != image_sha:
                                        raise ValueError("Frame integrity mismatch")
                                    temp.replace(target)
                                finally:
                                    temp.unlink(missing_ok=True)
                            db.execute("INSERT OR IGNORE INTO crawler_assets VALUES (?,?,?)",(image_sha,info["phash"],json.dumps({**info,"path":str(target)})))
                            metadata = {"video_sha":sha,"image_sha":image_sha,"frame_index":index,
                                        "estimated_seconds":index*interval,"quality":q}
                            cur = db.execute("INSERT OR IGNORE INTO video_frames VALUES (?,?,?,?,?)",(sha,index,interval,image_sha,json.dumps(metadata)))
                            report["frames"] += cur.rowcount
                        db.execute("INSERT OR IGNORE INTO frame_runs VALUES (?,?,?)",(sha,interval,maximum))
            except Exception as exc:
                report["errors"].append({"video_sha":sha,"error":type(exc).__name__})
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root",type=Path,default=Path("runtime/media-library"))
    p.add_argument("--interval",type=float,default=2)
    p.add_argument("--maximum",type=int,default=30)
    p.add_argument("--limit",type=int,default=20)
    a = p.parse_args()
    report = process(a.root,interval=a.interval,maximum=a.maximum,limit=a.limit)
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(bool(report["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
