import json

import pytest

from nail_media.batch import build_batch
from nail_media.task_store import TaskStore


def test_batch(tmp_path):
    config = json.loads((__import__("pathlib").Path("config/keywords.json")).read_text(encoding="utf-8"))
    batch = build_batch(config, platform="baidu", categories=["款式"], limit=3, max_tasks=2)
    assert len(batch) == 2
    assert all(t["enabled"] and t["platform"] == "baidu" and t["limit"] == 3 for t in batch)
    assert len({t["id"] for t in batch}) == 2


def test_batch_rejects_invalid_limits():
    config = {"platforms":["baidu"], "groups":{"款式":["法式"]}, "limit":20,
              "enabled":False, "interval_hours":24}
    with pytest.raises(ValueError):
        build_batch(config, limit=21)
    with pytest.raises(ValueError):
        build_batch(config, categories=["不存在"])


def test_stale_running_task_recovers(tmp_path):
    db = tmp_path / "tasks.sqlite3"
    store = TaskStore(db)
    store.register([{"id":"a"}])
    assert store.claim("a", now=100)
    assert store.recover(stale_after=60, now=159) == 0
    assert store.recover(stale_after=60, now=160) == 1
    assert TaskStore(db).claim("a", now=160)


def test_empty_results_scheduled_again(tmp_path):
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.register([{"id":"a"}])
    assert store.claim("a", now=100)
    store.finish("a", "empty_or_filtered", 1, now=101)
    assert not store.claim("a", now=3700)
    assert store.claim("a", now=3701)
