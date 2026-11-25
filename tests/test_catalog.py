from nail_media.catalog import Catalog
from nail_media.collectors import Media, HtmlCollector, platform_for
import pytest

def test_dedup(tmp_path):
    c = Catalog(tmp_path / "db.sqlite")
    m = Media("https://example.org/post", "https://example.org/a.jpg", "generic")
    assert c.add([m, m]) == 1
    assert c.add([m]) == 0
    assert c.export(tmp_path / "catalog.jsonl") == 1

def test_html():
    items = HtmlCollector().collect('<img src="/a.jpg"><img src="data:bad">', "https://example.org/post")
    assert len(items) == 1
    assert items[0].media_url == "https://example.org/a.jpg"

def test_secret_url():
    with pytest.raises(ValueError):
        Media("https://example.org/post", "https://example.org/a?token=x", "generic").record()

def test_platform():
    assert platform_for("https://www.douyin.com/video/123") == "douyin"
    assert platform_for("https://douyin.com.example.org/a") == "generic"
