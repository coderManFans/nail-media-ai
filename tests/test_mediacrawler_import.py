import json
import sqlite3
from PIL import Image
from nail_media.mediacrawler_import import import_batch


def test_offline_image_import(tmp_path):
    source = tmp_path / "source"
    media = source / "dy" / "media" / "12345"
    media.mkdir(parents=True)
    Image.new("RGB", (300, 400), "pink").save(media / "cover.jpg")
    manifest = source / "douyin" / "jsonl" / "search_contents_test.jsonl"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({
        "aweme_id": "12345", "aweme_url": "https://www.douyin.com/video/12345",
        "title": "nail art", "source_keyword": "nails",
        "video_download_url": "https://example.org/?token=secret"
    }) + "\n", encoding="utf-8")
    root = tmp_path / "library"
    first = import_batch(source, root)
    assert first["posts"] == first["images"] == 1
    assert not first["errors"]
    second = import_batch(source, root)
    assert second["images"] == 0
    assert second["duplicates"] == 1
    assert not second["errors"]
    with sqlite3.connect(root / "catalog.sqlite3") as db:
        assert db.execute("SELECT count(*) FROM imported_post_assets").fetchone()[0] == 1
        assert "secret" not in db.execute("SELECT payload FROM imported_posts").fetchone()[0]
    assert len(list((root / "images").glob("*.jpg"))) == 1


def test_invalid_source_and_missing_media(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    rows = [
        {"aweme_id": "../escape", "aweme_url": "https://www.douyin.com/video/1"},
        {"aweme_id": "123", "aweme_url": "https://www.douyin.com/video/123"},
    ]
    (source / "search_contents_test.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    report = import_batch(source, tmp_path / "library")
    assert report["posts"] == 1
    assert len(report["errors"]) == 2
