from nail_media.task_store import TaskStore

def test_persistence(tmp_path):
    path=tmp_path/"tasks.sqlite3"
    s=TaskStore(path)
    s.register([{"id":"a"}])
    assert s.claim("a",now=100)
    assert not TaskStore(path).claim("a",now=101)
    s.finish("a","success",24,now=102)
    assert not TaskStore(path).claim("a",now=103)
    assert s.claim("a",now=86502)

def test_retry(tmp_path):
    s=TaskStore(tmp_path/"tasks.sqlite3")
    s.register([{"id":"a"}])
    for now in (100,160,280):
        assert s.claim("a",now=now)
        s.finish("a","failed",24,now=now)
    assert s.rows()[0]["status"]=="failed"
    assert not s.claim("a",now=1000)
    assert s.reset("a")==1
    assert s.claim("a",now=1000)

def test_interrupted(tmp_path):
    s=TaskStore(tmp_path/"tasks.sqlite3")
    s.register([{"id":"a"}])
    assert s.claim("a",now=1)
    assert s.reset("a")==1
    assert s.claim("a",now=2)
