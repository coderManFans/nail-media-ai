from nail_media.pipeline import run_task
from nail_media.catalog import Catalog
from nail_media.collectors import Media

class Provider:
    def search(self,keyword,limit):
        return [Media("https://example.org/post","https://example.org/a.jpg","generic")]

def test_pipeline(tmp_path):
    c = Catalog(tmp_path/"db")
    t = {"id":"1","platform":"generic","keyword":"nail","limit":1}
    assert run_task(t,{},c,None,tmp_path)["status"] == "unconfigured"
    assert run_task(t,{"generic":Provider()},c,None,tmp_path)["inserted"] == 1
    assert run_task(t,{"generic":Provider()},c,None,tmp_path)["inserted"] == 0
