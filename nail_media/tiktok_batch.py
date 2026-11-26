"""Resumable, single-worker TikTok batch download into the shared local catalog.

Input is the JSON array emitted by nail_media.tiktok_discovery.
This module never performs TikTok keyword searches and never bypasses login gates.
Only process media you are authorized to retain.
"""
import argparse
import json
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlsplit

from .catalog import Catalog
from .tiktok_video import validate_tiktok_url
from .video_assets import ingest_video, sha256_file, SUPPORTED_EXTENSIONS


def download_video(url, work_dir, platform_id):
    """Download one public video via yt-dlp; return a local path and title."""
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("Install pip install -e '.[video]'") from exc
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    options = {
        "noplaylist": True, "quiet": True, "no_warnings": False,
        "restrictfilenames": True, "max_filesize": 500_000_000,
        "outtmpl": str(work_dir / "%(id)s.%(ext)s"),
    }
    with yt_dlp.YoutubeDL(options) as ydl:
        data = ydl.extract_info(url, download=True)
        info = ydl.sanitize_info(data)
    if str(info.get("id")) != platform_id:
        raise ValueError("Downloaded video ID differs from requested ID")
    matches = [
        p for p in work_dir.iterdir()
        if p.is_file() and not p.is_symlink() and p.stem == platform_id
        and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    if len(matches) != 1:
        raise ValueError("Expected one downloaded video file")
    return {"path": matches[0], "title": str(info.get("description") or info.get("title") or "")[:1000]}


def _database(path):
    db = sqlite3.connect(path, timeout=30)
    db.execute("""CREATE TABLE IF NOT EXISTS tiktok_batch_tasks (
        platform_id TEXT PRIMARY KEY, source_url TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0,
        updated_at REAL NOT NULL DEFAULT 0, sha256 TEXT, error_type TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS video_keywords (
        platform TEXT NOT NULL, platform_id TEXT NOT NULL, keyword TEXT NOT NULL,
        PRIMARY KEY(platform,platform_id,keyword))""")
    db.commit()
    return db


def _normalize(row):
    if not isinstance(row, dict):
        raise ValueError("Each task must be a JSON object")
    url = validate_tiktok_url(row.get("url"))
    if row.get("platform") not in (None, "tiktok"):
        raise ValueError("Expected TikTok platform")
    pid = urlsplit(url).path.rstrip("/").split("/")[-1]
    if not re.fullmatch(r"[0-9]{10,25}", pid):
        raise ValueError("Invalid video ID")
    if row.get("platform_id") is not None and str(row["platform_id"]) != pid:
        raise ValueError("Mismatching video ID")
    keyword = row.get("keyword")
    if not isinstance(keyword, str) or not keyword.strip() or len(keyword) > 200:
        raise ValueError("Expected non-empty keyword")
    return pid, "https://www.tiktok.com/@_/video/" + pid, keyword.strip()


def _existing_asset(db, root, pid):
    """Skip existing content only if its stored file is still present and intact."""
    tables = {r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )}
    if not {"video_sources", "video_assets"}.issubset(tables):
        return None
    for sha, payload in db.execute(
        """SELECT s.asset_sha, a.payload FROM video_sources s
        JOIN video_assets a ON a.sha256=s.asset_sha
        WHERE s.platform='tiktok' AND json_extract(s.payload,'$.platform_id')=?""",
        (pid,),
    ):
        asset = json.loads(payload)
        filename = asset.get("filename")
        if not isinstance(filename, str) or Path(filename).name != filename:
            continue
        path = root / "videos" / filename
        if path.is_file() and not path.is_symlink() and sha256_file(path) == sha:
            return sha
    return None


def run_batch(rows, root, *, downloader=download_video, ingester=ingest_video,
              max_items=20, retry_failed=False, recover_after=3600):
    if not isinstance(rows, list) or len(rows) > 5000:
        raise ValueError("Expected JSON array of at most 5000 tasks")
    if not 1 <= max_items <= 100 or recover_after <= 0:
        raise ValueError("Invalid max_items or recover_after")
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / "catalog.sqlite3"
    Catalog(path)
    report = {
        "submitted": 0, "downloaded": 0, "skipped_existing": 0,
        "skipped_failed": 0, "skipped_running": 0, "keywords_added": 0,
        "failed": [], "rejected": [],
    }
    unique = {}
    for index, row in enumerate(rows):
        try:
            pid, url, keyword = _normalize(row)
            unique.setdefault(pid, url)
            with _database(path) as db:
                db.execute(
                    """INSERT OR IGNORE INTO tiktok_batch_tasks
                    (platform_id,source_url) VALUES (?,?)""", (pid, url))
                report["keywords_added"] += db.execute(
                    """INSERT OR IGNORE INTO video_keywords
                    (platform,platform_id,keyword) VALUES ('tiktok',?,?)""",
                    (pid, keyword),
                ).rowcount
        except (ValueError, TypeError) as exc:
            report["rejected"].append({"index": index, "error": type(exc).__name__})
    report["submitted"] = len(unique)
    worked = 0
    for pid, url in unique.items():
        if worked >= max_items:
            break
        with _database(path) as db:
            existing = _existing_asset(db, root, pid)
            if existing:
                db.execute(
                    """UPDATE tiktok_batch_tasks SET state='success', sha256=?,
                    error_type=NULL, updated_at=? WHERE platform_id=?""",
                    (existing, time.time(), pid),
                )
                report["skipped_existing"] += 1
                continue
            state, updated = db.execute(
                "SELECT state,updated_at FROM tiktok_batch_tasks WHERE platform_id=?",
                (pid,),
            ).fetchone()
            if state == "running" and updated > time.time() - recover_after:
                report["skipped_running"] += 1
                continue
            if state == "failed" and not retry_failed:
                report["skipped_failed"] += 1
                continue
            db.execute(
                """UPDATE tiktok_batch_tasks SET state='running',
                attempts=attempts+1, updated_at=?, error_type=NULL
                WHERE platform_id=?""", (time.time(), pid),
            )
        worked += 1
        try:
            workspace = root / "tiktok-work" / pid
            workspace.mkdir(parents=True, exist_ok=True)
            output = downloader(url, workspace, pid)
            file = Path(output["path"])
            if not file.resolve().is_relative_to(workspace.resolve()):
                raise ValueError("Downloaded file must stay inside the task workspace")
            result = ingester(
                file, url, platform="tiktok", root=root, db_path=path,
                title=str(output.get("title") or "")[:1000], platform_id=pid,
            )
            sha = result["sha256"]
            with _database(path) as db:
                db.execute(
                    """UPDATE tiktok_batch_tasks SET state='success', sha256=?,
                    error_type=NULL, updated_at=? WHERE platform_id=?""",
                    (sha, time.time(), pid),
                )
            file.unlink(missing_ok=True)
            report["downloaded"] += 1
        except Exception as exc:
            kind = type(exc).__name__
            with _database(path) as db:
                db.execute(
                    """UPDATE tiktok_batch_tasks SET state='failed', error_type=?,
                    updated_at=? WHERE platform_id=?""",
                    (kind, time.time(), pid),
                )
            report["failed"].append({"platform_id": pid, "error": kind})
    report_path = root / "reports" / "tiktok-batch.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def task_status(root):
    path = Path(root) / "catalog.sqlite3"
    if not path.exists():
        return []
    with _database(path) as db:
        return [dict(zip(
            ("platform_id", "state", "attempts", "sha256", "error_type"), row,
        )) for row in db.execute(
            """SELECT platform_id,state,attempts,sha256,error_type
            FROM tiktok_batch_tasks ORDER BY platform_id"""
        )]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, help="JSON list from tiktok_discovery")
    p.add_argument("--root", type=Path, default=Path("runtime/media-library"))
    p.add_argument("--max-items", type=int, default=20)
    p.add_argument("--retry-failed", action="store_true")
    p.add_argument("--recover-after", type=int, default=3600)
    p.add_argument("--status", action="store_true")
    p.add_argument("--confirm-authorized", action="store_true")
    a = p.parse_args()
    if a.status:
        print(json.dumps(task_status(a.root), ensure_ascii=False, indent=2))
        return 0
    if not a.input or not a.confirm_authorized:
        p.error("--input and --confirm-authorized are required for downloading")
    report = run_batch(
        json.loads(a.input.read_text(encoding="utf-8")), a.root,
        max_items=a.max_items, retry_failed=a.retry_failed,
        recover_after=a.recover_after,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["failed"] or report["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
