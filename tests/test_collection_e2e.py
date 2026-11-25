import io
import sqlite3
import httpx
from PIL import Image
from nail_media.catalog import Catalog
from nail_media.collectors import Media
from nail_media.pipeline import run_task

def test_collection_e2e(tmp_path):
    buf=io.BytesIO()
    Image.new("RGB",(240,240),"red").save(buf,format="PNG")
    payload=buf.getvalue()
    urls=["https://example.org/a.png","https://example.org/b.png"]
    calls=[]
    class Provider:
        def search_page(self,keyword,limit,page):
            calls.append(page)
            return [Media("https://example.org/gallery",urls[page-1],"generic")] if page<=2 else []
    def handler(request):
        return httpx.Response(200,headers={"content-type":"image/png"},content=payload)
    catalog=Catalog(tmp_path/"catalog.sqlite3")
    task={"id":"e2e","platform":"generic","keyword":"美甲","limit":2}
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        first=run_task(task,{"generic":Provider()},catalog,client,tmp_path,urls,("example.org",))
        second=run_task(task,{"generic":Provider()},catalog,client,tmp_path,urls,("example.org",))
    assert calls==[1,2,1,2]
    assert first["status"]=="success"
    assert first["found"]==2
    assert first["inserted"]==2
    assert first["downloaded"]==1
    assert first["duplicates"]==1
    assert second["inserted"]==0
    assert second["downloaded"]==0
    assert second["duplicates"]==2
    with sqlite3.connect(catalog.path) as db:
        assert db.execute("SELECT COUNT(*) FROM media").fetchone()[0]==2
        assert db.execute("SELECT COUNT(*) FROM image_files").fetchone()[0]==1
    assert len(list((tmp_path/"images").iterdir()))==1
