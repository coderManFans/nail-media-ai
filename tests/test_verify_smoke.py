import json
import pytest
from nail_media.verify_smoke import verify

@pytest.mark.parametrize("status,found,ok",[("success",3,True),("success",0,False),("failed",3,False),("unconfigured",0,False)])
def test_verify(tmp_path,status,found,ok):
    p=tmp_path/"history.jsonl"
    p.write_text(json.dumps({"id":"a","status":status,"found":found}))
    if ok:
        assert verify(p,"a")==found
    else:
        with pytest.raises(ValueError):
            verify(p,"a")
