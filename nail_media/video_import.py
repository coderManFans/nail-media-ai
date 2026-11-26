"""Import an existing authorized local video without downloading it again."""
import argparse
import json
from pathlib import Path

from .video_assets import ingest_video


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path", type=Path)
    p.add_argument("--source-url", required=True)
    p.add_argument("--platform", choices=["tiktok", "douyin"], required=True)
    p.add_argument("--root", type=Path, default=Path("runtime/video-library"))
    p.add_argument("--db", type=Path)
    p.add_argument("--title", default="")
    p.add_argument("--platform-id", default="")
    args = p.parse_args()
    result = ingest_video(
        args.path, args.source_url, platform=args.platform, root=args.root,
        db_path=args.db, title=args.title, platform_id=args.platform_id,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
