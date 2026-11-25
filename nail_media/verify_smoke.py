import json
import sys
from pathlib import Path

def verify(path, task_id):
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    matches = [row for row in rows if row.get("id") == task_id]
    if not matches:
        raise ValueError("No execution report for requested task")
    latest = matches[-1]
    if latest.get("status") != "success" or latest.get("found",0) <= 0:
        raise ValueError("Live search did not return usable records: " + str({k:latest.get(k) for k in ("status","found","inserted","errors")}))
    return latest["found"]

if __name__ == "__main__":
    print("Verified candidate records:", verify(sys.argv[1],sys.argv[2]))
