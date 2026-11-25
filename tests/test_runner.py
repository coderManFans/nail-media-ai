import json
from nail_media.runner import execute
from nail_media.catalog import Catalog

def test_execution(tmp_path):
    f = tmp_path / "input.json"
    f.write_text(json.dumps([{"source_url":"https://www.douyin.com/video/123","media_type":"video"}]))
    tasks = [{"id":"a","enabled":True,"platform":"douyin","limit":1},{"id":"b","enabled":False}]
    c = Catalog(tmp_path / "db")
    inputs = {"a":{"adapter":"manifest","file":str(f)}}
    assert execute(tasks, inputs, c) == [{"id":"a","status":"success","inserted":1}]
    assert execute(tasks, inputs, c)[0]["inserted"] == 0
    assert execute(tasks, {}, c)[0]["status"] == "failed"
