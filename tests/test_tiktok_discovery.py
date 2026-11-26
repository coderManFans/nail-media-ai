import json
from nail_media.tiktok_discovery import ManifestProvider, discover


def test_manifest_keyword_and_dedup(tmp_path):
    p = tmp_path / "links.json"
    p.write_text(json.dumps([
        {"keyword":"nails","url":"https://www.tiktok.com/@one/video/1234567890123"},
        {"keyword":"nails","url":"https://www.tiktok.com/@two/video/1234567890123"},
        {"keyword":"nails","url":"https://example.org/@one/video/1234567890124"},
        {"keyword":"other","url":"https://www.tiktok.com/@one/video/1234567890125"},
    ]))
    rows = discover(ManifestProvider(p), "nails")
    assert len(rows) == 1
    assert rows[0]["platform_id"] == "1234567890123"
