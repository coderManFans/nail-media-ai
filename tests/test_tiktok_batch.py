import json
import sqlite3
import subprocess

from nail_media.tiktok_batch import run_batch, task_status
from nail_media.video_assets import ingest_video


def task(pid, keyword="cat eye nails"):
    return {
        "platform": "tiktok", "platform_id": pid, "keyword": keyword,
        "url": f"https://www.tiktok.com/@_/video/{pid}",
    }


def fake_ingester(file, url, **kwargs):
    def probe(*args, **kwargs):
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps({
                "streams": [{"codec_type": "video", "width": 640, "height": 360}],
                "format": {"duration": "53"},
            }),
        )
    return ingest_video(file, url, probe_runner=probe, **kwargs)


def test_batch_idempotency_and_keywords(tmp_path):
    calls = []
    def download(url, workspace, pid):
        calls.append(pid)
        file = workspace / (pid + ".mp4")
        file.write_bytes(("fake video " + pid).encode())
        return {"path": file, "title": "Nails"}
    a, b = "7363977699095891205", "7528966849250282757"
    rows = [task(a), task(a, "wedding nails"), task(b)]
    first = run_batch(rows, tmp_path, downloader=download, ingester=fake_ingester)
    assert first["submitted"] == first["downloaded"] == 2
    assert first["keywords_added"] == 3
    assert not first["failed"] and not first["rejected"]
    second = run_batch(rows, tmp_path, downloader=download, ingester=fake_ingester)
    assert second["downloaded"] == 0 and second["skipped_existing"] == 2
    assert len(calls) == 2
    assert len(list((tmp_path / "videos").glob("*.mp4"))) == 2
    with sqlite3.connect(tmp_path / "catalog.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM video_keywords").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM video_sources").fetchone()[0] == 2
    assert [r["state"] for r in task_status(tmp_path)] == ["success", "success"]


def test_failure_isolation_and_explicit_retry(tmp_path):
    a, b = "7363977699095891205", "7528966849250282757"
    calls = []
    def unstable(url, workspace, pid):
        calls.append(pid)
        if pid == a:
            raise RuntimeError("unavailable")
        file = workspace / (pid + ".mp4")
        file.write_bytes(b"video " + pid.encode())
        return {"path": file}
    first = run_batch([task(a), task(b)], tmp_path,
                      downloader=unstable, ingester=fake_ingester)
    assert len(first["failed"]) == 1 and first["downloaded"] == 1
    second = run_batch([task(a), task(b)], tmp_path,
                       downloader=unstable, ingester=fake_ingester)
    assert second["skipped_failed"] == 1 and second["skipped_existing"] == 1
    def repaired(url, workspace, pid):
        file = workspace / (pid + ".mp4")
        file.write_bytes(b"recovered video")
        return {"path": file}
    third = run_batch([task(a), task(b)], tmp_path,
                      downloader=repaired, ingester=fake_ingester,
                      retry_failed=True)
    assert third["downloaded"] == 1 and not third["failed"]
    assert all(r["state"] == "success" for r in task_status(tmp_path))


def test_invalid_url_and_stale_task_recovery(tmp_path):
    pid = "7363977699095891205"
    def download(url, workspace, pid):
        file = workspace / (pid + ".mp4")
        file.write_bytes(b"video")
        return {"path": file}
    # No downloader call is made for invalid URLs.
    bad = dict(task(pid), url="https://www.tiktok.com/@_/video/" + pid + "?token=secret")
    result = run_batch([bad], tmp_path, downloader=lambda *args: 1,
                       ingester=fake_ingester)
    assert result["submitted"] == 0 and len(result["rejected"]) == 1
    assert not task_status(tmp_path)
    # Simulate an interrupted worker whose lease has expired.
    valid = task(pid)
    run_batch([valid], tmp_path, downloader=download, ingester=fake_ingester)
    with sqlite3.connect(tmp_path / "catalog.sqlite3") as db:
        db.execute("DELETE FROM video_sources")
        db.execute("UPDATE tiktok_batch_tasks SET state='running',updated_at=1")
    recovered = run_batch([valid], tmp_path, downloader=download,
                          ingester=fake_ingester, recover_after=3600)
    assert recovered["downloaded"] == 1
    assert task_status(tmp_path)[0]["state"] == "success"


def test_limits(tmp_path):
    from pytest import raises
    with raises(ValueError):
        run_batch([], tmp_path, max_items=0)
    with raises(ValueError):
        run_batch([], tmp_path, recover_after=0)
