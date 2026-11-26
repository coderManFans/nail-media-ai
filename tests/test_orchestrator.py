from nail_media.orchestrator import run_cycle
from nail_media.task_store import TaskStore


def test_four_platforms_and_failure_isolation(tmp_path):
    tasks = [{"id":p,"platform":p,"enabled":True,"limit":3}
             for p in ("baidu","xiaohongshu","douyin","tiktok")]
    store = TaskStore(tmp_path / "tasks.sqlite3")
    store.register(tasks)
    def execute(task, root):
        if task["platform"] == "baidu":
            raise RuntimeError("test")
        return {"status":"success"}
    results = run_cycle(tasks,tmp_path,store,executor=execute)
    assert len(results) == 4
    assert results[0]["status"] == "failed"
    assert all(r["status"] == "success" for r in results[1:])
    assert not run_cycle(tasks,tmp_path,store,executor=execute)
    assert len((tmp_path / "collection-history.jsonl").read_text().splitlines()) == 4
