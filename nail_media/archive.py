import argparse
import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from .catalog import Catalog


def merge_records(existing, incoming):
    """Merge catalog JSONL by typed ID, retaining observation history."""
    merged = {}
    for item in [*existing, *incoming]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError("Invalid catalog record")
        key = (item.get("record_type", "media"), item["id"])
        previous = merged.get(key)
        if previous is not None and key[0] == "image_asset":
            if previous.get("sha256") != item.get("sha256"):
                raise ValueError("Conflicting image identity")
            observations = {}
            for obs in [*previous.get("observations", []), *item.get("observations", [])]:
                name = (obs["platform"], obs["keyword"], obs["observed_sha"])
                observations[name] = obs
            item = {**previous, **item, "observations": [
                observations[name] for name in sorted(observations)
            ]}
        if previous is not None and key[0] == "video_asset":
            if previous.get("sha256") != item.get("sha256"):
                raise ValueError("Conflicting video identity")
            sources = {}
            for source in [*previous.get("sources", []), *item.get("sources", [])]:
                sources[source["media_id"]] = source
            item = {**previous, **item, "sources": [
                sources[name] for name in sorted(sources)
            ]}
        merged[key] = item
    return [merged[k] for k in sorted(merged)]


def read_jsonl(path):
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def stage_catalog(db, checkout):
    root = Path(checkout).resolve()
    actual = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True
    ).strip()
    if Path(actual).resolve() != root:
        raise ValueError("Expected a dedicated repository checkout")
    remote = subprocess.check_output(
        ["git", "-C", str(root), "remote", "get-url", "origin"], text=True
    ).strip()
    if remote not in {
        "https://github.com/coderManFans/nail-media-data.git",
        "git@github.com:coderManFans/nail-media-data.git",
        "https://github.com/coderManFans/nail-media-data",
    }:
        raise ValueError("Unexpected archive repository")
    target = root / "catalog" / "media.jsonl"
    if not target.resolve().is_relative_to(root):
        raise ValueError("Invalid archive path")
    with TemporaryDirectory() as directory:
        candidate = Path(directory) / "media.jsonl"
        Catalog(Path(db)).export(candidate)
        records = merge_records(read_jsonl(target), read_jsonl(candidate))
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_suffix(".jsonl.tmp")
    staged.write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in records),
        encoding="utf-8",
    )
    staged.replace(target)
    return len(records)


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
