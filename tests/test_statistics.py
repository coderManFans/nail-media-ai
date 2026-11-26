import json
import sqlite3
from nail_media.catalog import Catalog
from nail_media.statistics import statistics


def test_empty_and_post_export(tmp_path):
    path = tmp_path / "catalog.sqlite3"
    catalog = Catalog(path)
    assert statistics(path)["counts"]["imported_posts"] == 0
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE imported_posts (platform_id TEXT PRIMARY KEY,payload TEXT)")
        db.execute("CREATE TABLE imported_post_assets (platform_id TEXT,sha256 TEXT,kind TEXT)")
        db.execute("INSERT INTO imported_posts VALUES (?,?)", ("123",json.dumps({
            "platform":"douyin","platform_id":"123","source_url":"https://www.douyin.com/video/123",
            "title":"Nails","keyword":"美甲","xsec_token":"secret"})))
        db.execute("INSERT INTO imported_post_assets VALUES ('123','abc','image')")
    assert statistics(path)["platforms"]["douyin"]["posts"] == 1
    output = tmp_path / "export.jsonl"
    assert catalog.export(output) == 1
    post = json.loads(output.read_text())
    assert post["id"] == "douyin:123"
    assert post["assets"] == [{"sha256":"abc","kind":"image"}]
    assert "secret" not in output.read_text()
