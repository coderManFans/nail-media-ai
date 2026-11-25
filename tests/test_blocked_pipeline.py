import httpx
from nail_media.catalog import Catalog
from nail_media.pipeline import run_task

class Blocked:
    def search(self,keyword,limit):
        raise PermissionError("Access denied")

def test_blocked(tmp_path):
    with httpx.Client() as client:
        report=run_task({"id":"test","platform":"baidu","keyword":"美甲","limit":3},{"baidu":Blocked()},Catalog(tmp_path/"db.sqlite"),client,tmp_path)
    assert report["status"]=="blocked"
    assert report["found"]==0
