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


def test_xhs_detail_import(tmp_path):
    pid = "abcdef123456789012345678"
    source = tmp_path / "source"
    folder = source / "xhs" / "media" / pid
    folder.mkdir(parents=True)
    for i, color in enumerate(("pink", "red", "blue"), 1):
        Image.new("RGB", (300, 400), color).save(folder / f"{i:03}.webp")
    manifest = source / "xhs" / "jsonl" / "detail_contents_test.jsonl"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps({
        "note_id": pid, "note_url": f"https://www.xiaohongshu.com/discovery/item/{pid}?xsec_token=secret",
        "type": "normal", "title": "Wedding nails", "xsec_token": "secret",
        "image_list": "https://example.org/?token=secret"
    }) + "\n", encoding="utf-8")
    root = tmp_path / "library"
    first = import_batch(source, root, platform="xiaohongshu")
    assert first["posts"] == 1 and first["images"] == 3
    assert not first["errors"]
    second = import_batch(source, root, platform="xiaohongshu")
    assert second["duplicates"] == 3 and second["images"] == 0
    with sqlite3.connect(root / "catalog.sqlite3") as db:
        key, payload = db.execute("SELECT platform_id,payload FROM imported_posts").fetchone()
        assert key == "xiaohongshu:" + pid
        assert "secret" not in payload
        assert json.loads(payload)["source_url"] == "https://www.xiaohongshu.com/explore/" + pid
        assert db.execute("SELECT count(*) FROM imported_post_assets").fetchone()[0] == 3
