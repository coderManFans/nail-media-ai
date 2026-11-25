import json
import argparse
from pathlib import Path
from hashlib import sha256

def plan(config):
    for category, terms in config["groups"].items():
        for term in terms:
            keyword = term if term.endswith("美甲") else term + "美甲"
            for platform in config["platforms"]:
                key = sha256((platform + ":" + keyword).encode()).hexdigest()[:20]
                yield {"id": key, "category": category, "keyword": keyword, "platform": platform, "limit": config["limit"], "interval_hours": config["interval_hours"], "enabled": config["enabled"], "status": "pending_configuration"}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="config/keywords.json")
    p.add_argument("--output", default="runtime/tasks.json")
    a = p.parse_args()
    tasks = list(plan(json.loads(Path(a.config).read_text(encoding="utf-8"))))
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(tasks)} task definitions; no network requests executed.")

if __name__ == "__main__":
    main()
