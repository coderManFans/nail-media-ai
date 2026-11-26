import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from nail_media.archive import merge_records
from nail_media.catalog import Catalog
from nail_media.video_assets import ingest_video, inspect_video, validate_source


def fake_probe(*args, **kwargs):
    return SimpleNamespace(stdout=json.dumps({
        "streams": [{"codec_type": "video", "width": 640, "height": 360}],
        "format": {"duration": "53.0"},
    }))


def test_import_deduplicates_and_exports(tmp_path):
    raw = tmp_path / "source.mp4"
    raw.write_bytes(b"fake local video data for deterministic test")
    library = tmp_path / "library"
    url = "https://www.tiktok.com/@_/video/7363977699095891205"
    first = ingest_video(raw, url, platform="tiktok", root=library,
                         title="Simple Flower", probe_runner=fake_probe)
    second = ingest_video(raw, url, platform="tiktok", root=library,
                          title="Simple Flower", probe_runner=fake_probe)
    assert first["new_file"] and first["new_source"]
    assert not second["new_file"] and not second["new_source"]
    assert len(list((library / "videos").iterdir())) == 1
    with sqlite3.connect(library / "catalog.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM video_assets").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM video_sources").fetchone()[0] == 1
    output = tmp_path / "catalog.jsonl"
    assert Catalog(library / "catalog.sqlite3").export(output) == 2
    items = [json.loads(x) for x in output.read_text().splitlines()]
    asset = next(item for item in items if item.get("record_type") == "video_asset")
    assert asset["filename"].endswith(".mp4")
    assert asset["duration_seconds"] == 53
    assert asset["sources"][0]["source_url"] == url
    assert all(str(tmp_path) not in json.dumps(r) for r in items)


def test_video_asset_archive_merge():
    previous = {"id": "sha", "record_type": "video_asset", "sha256": "sha",
                "sources": [{"media_id": "a", "source_url": "https://www.tiktok.com/a"}]}
    incoming = {"id": "sha", "record_type": "video_asset", "sha256": "sha",
                "sources": [{"media_id": "b", "source_url": "https://www.tiktok.com/b"}]}
    merged = merge_records([previous], [incoming])
    assert [source["media_id"] for source in merged[0]["sources"]] == ["a", "b"]


def test_rejects_wrong_platform_and_unsupported_file(tmp_path):
    with pytest.raises(ValueError):
        validate_source("https://evil.example.com/video", "tiktok")
    with pytest.raises(ValueError):
        validate_source("https://www.tiktok.com/@_/video/7363977699095891205?token=secret", "tiktok")
    with pytest.raises(ValueError):
        inspect_video(tmp_path / "missing.mp4", probe_runner=fake_probe)
    invalid = tmp_path / "something.txt"
    invalid.write_bytes(b"not a movie")
    with pytest.raises(ValueError):
        inspect_video(invalid, probe_runner=fake_probe)
