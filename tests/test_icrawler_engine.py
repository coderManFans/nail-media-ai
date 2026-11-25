import sqlite3
from PIL import Image
from nail_media.catalog import Catalog
from nail_media.icrawler_engine import run_icrawler_task

def test_ingestion(tmp_path):
    def crawl(keyword,limit,directory):
        Image.new("RGB",(240,240),"red").save(directory/"a.png")
        Image.new("RGB",(240,240),"red").save(directory/"b.png")
    catalog=Catalog(tmp_path/"catalog.sqlite3")
    task={"id":"baidu-test","keyword":"猫眼美甲","limit":2}
    first=run_icrawler_task(task,catalog,tmp_path,crawl=crawl)
    second=run_icrawler_task(task,catalog,tmp_path,crawl=crawl)
    assert first["status"]=="success"
    assert first["found"]==2
    assert first["downloaded"]==1
    assert first["duplicates"]==1
    assert second["downloaded"]==0
    assert second["inserted"]==0
    with sqlite3.connect(catalog.path) as db:
        assert db.execute("SELECT COUNT(*) FROM crawler_assets").fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM crawler_observations").fetchone()[0]==1
    assert len(list((tmp_path/"images").iterdir()))==1
