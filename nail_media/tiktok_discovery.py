"""Offline discovery adapter for authorized video link exports."""
import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit
from typing import Protocol
from .tiktok_video import validate_tiktok_url


class DiscoveryProvider(Protocol):
    def search(self, keyword: str, limit: int) -> list[str]: ...


class ManifestProvider:
    def __init__(self, path):
        self.path = Path(path)

    def search(self, keyword, limit):
        rows = json.loads(self.path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError("Expected JSON array")
        return [r["url"] for r in rows if isinstance(r, dict)
                and r.get("keyword") == keyword and isinstance(r.get("url"), str)]


def discover(provider, keyword, limit=5):
    if not keyword.strip() or not 1 <= limit <= 20:
        raise ValueError("Invalid keyword or limit")
    result = []
    seen = set()
    for url in provider.search(keyword, limit):
        try:
            validate_tiktok_url(url)
            pid = urlsplit(url).path.rstrip("/").split("/")[-1]
        except (ValueError, TypeError):
            continue
        if pid in seen:
            continue
        seen.add(pid)
        result.append({"platform": "tiktok", "platform_id": pid,
                       "keyword": keyword, "url": "https://www.tiktok.com/@_/video/" + pid})
        if len(result) >= limit:
            break
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--keyword", required=True)
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    rows = discover(ManifestProvider(a.input), a.keyword, a.limit)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"found": len(rows)}, ensure_ascii=False))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
