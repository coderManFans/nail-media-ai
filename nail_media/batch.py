"""Prepare a safe, opt-in batch from the existing keyword taxonomy."""
import argparse
import json
from pathlib import Path

from .tasks import plan


def build_batch(config, *, platform="baidu", categories=None, limit=5,
                max_tasks=10, interval_hours=24):
    if not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    if not 1 <= max_tasks <= 100:
        raise ValueError("max_tasks must be 1..100")
    if interval_hours < 1:
        raise ValueError("interval_hours must be positive")
    if platform not in config["platforms"]:
        raise ValueError("unknown platform")
    allowed = set(categories) if categories else set(config["groups"])
    if allowed - set(config["groups"]):
        raise ValueError("unknown categories")
    result = []
    for task in plan(config):
        if task["platform"] != platform or task["category"] not in allowed:
            continue
        result.append({
            **task, "limit": limit, "interval_hours": interval_hours,
            "enabled": True,
        })
        if len(result) >= max_tasks:
            break
    return result


def main():
    p = argparse.ArgumentParser(description="Prepare an opt-in keyword batch (no network access)")
    p.add_argument("--config", default="config/keywords.json")
    p.add_argument("--output", default="runtime/baidu-batch.json")
    p.add_argument("--platform", default="baidu")
    p.add_argument("--category", action="append", default=[])
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--max-tasks", type=int, default=10)
    p.add_argument("--interval-hours", type=int, default=24)
    a = p.parse_args()
    config = json.loads(Path(a.config).read_text(encoding="utf-8"))
    tasks = build_batch(
        config, platform=a.platform, categories=a.category or None,
        limit=a.limit, max_tasks=a.max_tasks, interval_hours=a.interval_hours,
    )
    output = Path(a.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(tasks)} enabled tasks at {output}; no network requests executed.")


if __name__ == "__main__":
    main()
