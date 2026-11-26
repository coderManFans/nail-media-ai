from nail_media.production_pipeline import execute,status

def test_resume(tmp_path):
    calls=[]
    def first():
        calls.append("first")
        return {}
    def fail():
        return {"errors":["test"]}
    result=execute(tmp_path,[("first",first),("second",fail)])
    assert result["state"]=="failed"
    result=execute(tmp_path,[("first",first),("second",lambda:{})],resume=True)
    assert result["state"]=="success"
    assert calls==["first"]
    assert len(status(tmp_path)["steps"])==2
