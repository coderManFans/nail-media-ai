import argparse
import json
import subprocess
from pathlib import Path
from .catalog import Catalog

def stage_catalog(db, checkout):
    root = Path(checkout).resolve()
    actual = subprocess.check_output(["git","-C",str(root),"rev-parse","--show-toplevel"], text=True).strip()
    if Path(actual).resolve() != root:
        raise ValueError("Expected a dedicated repository checkout")
    remote = subprocess.check_output(["git","-C",str(root),"remote","get-url","origin"], text=True).strip()
    if remote not in {"https://github.com/coderManFans/nail-media-data.git","git@github.com:coderManFans/nail-media-data.git","https://github.com/coderManFans/nail-media-data"}:
        raise ValueError("Unexpected archive repository")
    target = root / "catalog" / "media.jsonl"
    if not target.resolve().is_relative_to(root):
        raise ValueError("Invalid archive path")
    return Catalog(Path(db)).export(target)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="runtime/catalog.sqlite3")
    p.add_argument("--checkout", required=True)
    p.add_argument("--confirm-authorized", action="store_true")
    a = p.parse_args()
    if not a.confirm_authorized:
        p.error("Review metadata and confirm permission before export")
    print(stage_catalog(a.db, a.checkout), "records exported; review before git commit/push")

if __name__ == "__main__":
    main()
