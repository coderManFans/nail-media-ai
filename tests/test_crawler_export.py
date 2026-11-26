import json
from PIL import Image
from nail_media.catalog import Catalog
from nail_media.icrawler_engine import run_icrawler_task

def test_export(tmp_path):
    catalog=Catalog(tmp_path/"catalog.sqlite3")
    def crawl(keyword,limit,directory):
        Image.new("RGB",(240,240),"red").save(directory/"a.png")
    report=run_icrawler_task({"id":"test","keyword":"猫眼美甲","limit":1},catalog,tmp_path,crawl=crawl)
    assert report["status"]=="success"
    output=tmp_path/"media.jsonl"
    assert catalog.export(output)==1
    record=json.loads(output.read_text())
    assert record["record_type"]=="image_asset"
    assert record["filename"].endswith(".png")
    assert record["observations"][0]["keyword"]=="猫眼美甲"
    assert "path" not in record
    assert str(tmp_path) not in output.read_text()
