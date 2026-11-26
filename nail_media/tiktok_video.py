"""Standalone yt-dlp video smoke test and normalized metadata import.

Only run on publicly accessible videos you are permitted to retain.
No TikTok account, paid API, or platform API SDK is required.
"""
import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from .catalog import Catalog
from .collectors import Media

VIDEO_RE = re.compile(r"^/(@[^/]+/video/|@_/video/)([0-9]{10,25})/?$")

def validate_tiktok_url(value):
    parts = urlsplit(value)
    if (parts.scheme != "https" or parts.hostname not in
            {"www.tiktok.com", "tiktok.com"} or parts.username or parts.password
            or parts.port or parts.query or parts.fragment):
        raise ValueError("Expected a canonical public TikTok video URL")
    if not VIDEO_RE.fullmatch(parts.path):
        raise ValueError("Expected /@username/video/1234567890")
    return value


def normalize_info(info, source_url):
    video_id = str(info.get("id") or "")
    if not video_id.isdecimal():
        raise ValueError("Missing numeric TikTok video ID")
    title = str(info.get("description") or info.get("title") or "")
    duration = info.get("duration")
    if duration is not None and not isinstance(duration, (float, int)):
        raise ValueError("Invalid duration")
    media = Media(source_url, source_url, "tiktok", "video", title)
    record = media.record()
    return {
        "record": record,
        "source_url": source_url,
        "platform_id": video_id,
        "duration_seconds": duration,
        "title": title,
        "uploader": str(info.get("uploader") or ""),
        "license_status": "unknown",
    }


def probe(url, *, download=False, root=Path("runtime/tiktok-smoke"), client=None):
    url = validate_tiktok_url(url)
    try:
        import yt_dlp
    except ImportError as exc:
        raise RuntimeError("Install with pip install -e '.[video]'") from exc
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    opts = {
        "noplaylist": True,
        "skip_download": not download,
        "quiet": True,
        "no_warnings": False,
        "outtmpl": str(root / "%(id)s.%(ext)s"),
        "writeinfojson": bool(download),
        "restrictfilenames": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(url, download=download)
        info = ydl.sanitize_info(data)
    item = normalize_info(info, url)
    return {"video": item, "download_requested": download}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--download", action="store_true",
                   help="Explicit opt-in; requires permission to retain video")
    p.add_argument("--root", type=Path, default=Path("runtime/tiktok-smoke"))
    p.add_argument("--db", type=Path, help="Optional catalog database for source URL")
    a = p.parse_args()
    result = probe(a.url, download=a.download, root=a.root)
    if a.db:
        v = result["video"]
        Catalog(a.db).add([
            Media(v["source_url"], v["source_url"], "tiktok", "video", v["title"])
        ])
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
