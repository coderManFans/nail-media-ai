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


def test_review_soft_failure(tmp_path):
    result=execute(tmp_path,[("review",lambda:{"failed":3}),("export",lambda:{"records":1})])
    assert result["state"]=="success_with_warnings"
    assert result["warnings"]==["review"]
    assert status(tmp_path)["steps"][-1]["state"]=="success"

def test_validation_hard_failure(tmp_path):
    result=execute(tmp_path,[("review",lambda:{"failed":1}),("validate",lambda:{"errors":["orphan"]}),("export",lambda:{})])
    assert result["state"]=="failed"
    assert result["stage"]=="validate"
