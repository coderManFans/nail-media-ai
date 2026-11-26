"""Verified local video ingestion shared by TikTok and Douyin adapters.

The media itself stays local. Only sanitized metadata is archived.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import urlsplit

from .collectors import Media, platform_for

SUPPORTED_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
MAX_BYTES = 500_000_000
STREAM_BYTES = 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(STREAM_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_source(source_url: str, platform: str):
    if platform not in {"tiktok", "douyin", "xiaohongshu"}:
        raise ValueError("Unsupported video source platform")
    if platform_for(source_url) != platform:
        raise ValueError("Source URL does not match platform")
    parts = urlsplit(source_url)
    if (parts.scheme != "https" or parts.username or parts.password
            or parts.query or parts.fragment):
        raise ValueError("Source URL must be public HTTPS without query/fragment")
    return source_url


def inspect_video(path: Path, *, probe_runner=subprocess.run):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("Video file must exist and must not be a symlink")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported video extension")
    size = path.stat().st_size
    if not 0 < size <= MAX_BYTES:
        raise ValueError("Video size outside limits")
    try:
        result = probe_runner(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,width,height",
             "-of", "json", str(path)],
            capture_output=True, text=True, check=True, timeout=25,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe unavailable: install ffmpeg") from exc
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise ValueError("Video probe failed") from exc
    metadata = json.loads(result.stdout)
    streams = [s for s in metadata.get("streams", []) if s.get("codec_type") == "video"]
    if not streams:
        raise ValueError("No video stream found")
    width = int(streams[0].get("width") or 0)
    height = int(streams[0].get("height") or 0)
    duration = float(metadata.get("format", {}).get("duration") or 0)
    if not (0 < width <= 7680 and 0 < height <= 4320 and 0 < duration <= 7200):
        raise ValueError("Invalid video dimensions or duration")
    return {
        "sha256": sha256_file(path), "size_bytes": size,
        "width": width, "height": height, "duration_seconds": round(duration, 3),
        "extension": path.suffix.lower(),
    }


def ingest_video(path, source_url, *, platform, root, db_path=None,
                 title="", platform_id="", probe_runner=subprocess.run):
    source_url = validate_source(source_url, platform)
    path, root = Path(path), Path(root)
    info = inspect_video(path, probe_runner=probe_runner)
    store = root / "videos"
    store.mkdir(parents=True, exist_ok=True)
    db_path = Path(db_path) if db_path else root / "catalog.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    media = Media(source_url, source_url, platform, "video", str(title))
    record = media.record()
    sha = info["sha256"]
    target = store / (sha + info["extension"])
    new_file = False
    if not target.is_file():
        temp = store / (sha + ".part")
        try:
            shutil.copyfile(path, temp)
            if sha256_file(temp) != sha:
                raise ValueError("Video changed during ingest")
            temp.replace(target)
            new_file = True
        finally:
            temp.unlink(missing_ok=True)
    with sqlite3.connect(db_path, timeout=30) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS video_assets (
            sha256 TEXT PRIMARY KEY, payload TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS video_sources (
            media_id TEXT PRIMARY KEY, platform TEXT NOT NULL,
            source_url TEXT NOT NULL, asset_sha TEXT NOT NULL,
            payload TEXT NOT NULL)""")
        db.execute("CREATE TABLE IF NOT EXISTS media (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
        asset = {**info, "filename": target.name, "media_type": "video",
                 "license_status": "unknown"}
        db.execute("INSERT OR IGNORE INTO video_assets VALUES (?, ?)",
                   (sha, json.dumps(asset, ensure_ascii=False)))
        source = {
            "media_id": record["id"], "source_url": source_url, "platform": platform,
            "platform_id": str(platform_id), "title": str(title), "asset_sha": sha,
        }
        inserted = db.execute(
            "INSERT OR IGNORE INTO video_sources VALUES (?, ?, ?, ?, ?)",
            (record["id"], platform, source_url, sha,
             json.dumps(source, ensure_ascii=False)),
        ).rowcount
        db.execute("INSERT OR IGNORE INTO media VALUES (?, ?)",
                   (record["id"], json.dumps(record, ensure_ascii=False)))
    return {"status": "success", "platform": platform, "sha256": sha,
            "filename": target.name, "new_file": new_file, "new_source": bool(inserted),
            "duration_seconds": info["duration_seconds"],
            "db": str(db_path)}
