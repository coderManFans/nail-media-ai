import argparse
import json
from pathlib import Path
from .catalog import Catalog
from .collectors import ManifestCollector, HtmlCollector

class Registry:
    def __init__(self):
        self.adapters = {"manifest": ManifestCollector(), "html": HtmlCollector()}
    def collect(self, adapter, payload, source=""):
        if adapter not in self.adapters:
            raise ValueError(f"Adapter not configured: {adapter}")
        return self.adapters[adapter].collect(payload, source)

def execute(tasks, inputs, catalog):
    registry = Registry()
    results = []
    for task in tasks:
        if not task.get("enabled"):
            continue
        try:
            spec = inputs[task["id"]]
            items = registry.collect(spec["adapter"], Path(spec["file"]).read_text(encoding="utf-8"), spec.get("source", ""))
            items = [i for i in items if i.platform == task["platform"]][:task["limit"]]
            results.append({"id": task["id"], "status": "success", "inserted": catalog.add(items)})
        except Exception as exc:
            results.append({"id": task["id"], "status": "failed", "error_type": type(exc).__name__})
    return results

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tasks", default="runtime/tasks.json")
    p.add_argument("--inputs", required=True)
    p.add_argument("--db", default="runtime/catalog.sqlite3")
    p.add_argument("--report", default="runtime/report.json")
    a = p.parse_args()
    read = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
    results = execute(read(a.tasks), read(a.inputs), Catalog(Path(a.db)))
    report = Path(a.report)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Executed {len(results)} enabled tasks")
    return int(any(r["status"] == "failed" for r in results))

if __name__ == "__main__":
    raise SystemExit(main())
