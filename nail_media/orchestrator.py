"""Single-worker orchestration of existing collection adapters."""
import argparse
import json
import time
from pathlib import Path
from .catalog import Catalog
from .task_store import TaskStore
from .icrawler_engine import run_icrawler_task
from .mediacrawler_import import import_batch
from .tiktok_batch import run_batch
from .tiktok_discovery import discover, ManifestProvider


def load_config(path):
    path = Path(path).resolve()
    config = json.loads(path.read_text(encoding="utf-8"))
    root = (path.parent / config["root"]).resolve()
    tasks = config["tasks"]
    ids = set()
    for task in tasks:
        if task["id"] in ids or task["platform"] not in {"baidu","xiaohongshu","douyin","tiktok"}:
            raise ValueError("Duplicate ID or unsupported platform")
        ids.add(task["id"])
        if not 1 <= task["limit"] <= 20 or task.get("interval_hours",24) < 1:
            raise ValueError("Invalid task limits")
        if "input" in task:
            task["input"] = str((path.parent / task["input"]).resolve())
    return root, tasks


def execute(task, root):
    platform = task["platform"]
    if platform == "baidu":
        return run_icrawler_task(task, Catalog(root / "catalog.sqlite3"), root)
    source = Path(task["input"])
    if not source.exists():
        return {"status":"unconfigured","errors":["missing_input"]}
    if platform in {"douyin","xiaohongshu"}:
        report = import_batch(source, root, task["limit"], platform)
        return {**report,"status":"partial" if report["errors"] else
                ("success" if report["posts"] else "empty_or_filtered")}
    rows = discover(ManifestProvider(source), task["keyword"], task["limit"])
    report = run_batch(rows, root, max_items=task["limit"], retry_failed=True)
    return {**report,"status":"partial" if any(report[k] for k in
            ("failed","rejected","skipped_running","skipped_failed")) else
            ("success" if rows else "empty_or_filtered")}


def run_cycle(tasks, root, store, *, executor=execute):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    results = []
    for task in tasks:
        if not task.get("enabled",False) or not store.claim(task["id"]):
            continue
        try:
            report = executor(task, root)
        except Exception as exc:
            report = {"status":"failed","errors":[type(exc).__name__]}
        store.finish(task["id"], report["status"], task.get("interval_hours",24))
        result = {**report,"id":task["id"],"platform":task["platform"]}
        results.append(result)
        with (root / "collection-history.jsonl").open("a",encoding="utf-8") as fp:
            fp.write(json.dumps(result,ensure_ascii=False)+"\n")
    return results


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config",type=Path,default=Path("config/collection.json"))
    p.add_argument("--once",action="store_true")
    p.add_argument("--status",action="store_true")
    p.add_argument("--reset-task")
    p.add_argument("--confirm-authorized",action="store_true")
    a = p.parse_args()
    root,tasks = load_config(a.config)
    store = TaskStore(root / "collection-tasks.sqlite3")
    store.register(tasks)
    if a.status:
        print(json.dumps(store.rows(),ensure_ascii=False,indent=2))
        return 0
    if a.reset_task:
        print(store.reset(a.reset_task))
        return 0
    if not a.confirm_authorized:
        p.error("Confirm permission to collect and retain media")
    store.recover()
    while True:
        results = run_cycle(tasks,root,store)
        print(json.dumps(results,ensure_ascii=False,indent=2),flush=True)
        if a.once:
            return int(any(r["status"] not in {"success","empty_or_filtered"} for r in results))
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
