import json
from pathlib import Path
from nail_media.tasks import plan

def test_defaults():
    tasks = list(plan(json.loads(Path("config/keywords.json").read_text())))
    assert len(tasks) == 108
    assert len({t["id"] for t in tasks}) == len(tasks)
    assert not any(t["enabled"] for t in tasks)
