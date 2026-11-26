import json
import sqlite3
import pytest
from PIL import Image
from nail_media.tag_schema import Tags
from nail_media.tag_pipeline import run
from nail_media.video_assets import sha256_file

def sample():
    return dict(is_nail_art=True,image_quality="high",colors=["裸粉色"],
        styles=["法式"],nail_shape="杏仁甲",nail_length="中长甲",
        decorations=[],finish=["亮面"],scenes=[],seasons=[],
        visual_evidence="粉色甲面",inference_evidence="",description="粉色法式",
        confidence=0.9,inference_confidence=0.0)

def test_schema():
    assert not Tags.model_validate(sample()).result()["need_review"]
    with pytest.raises(ValueError):
        Tags.model_validate({**sample(),"colors":["invented"]})
    assert Tags.model_validate({**sample(),"is_nail_art":False}).result()["colors"] == []

def test_resume(tmp_path):
    (tmp_path/"images").mkdir()
    image = tmp_path/"images"/"a.jpg"
    Image.new("RGB",(320,320),"pink").save(image)
    sha = sha256_file(image)
    with sqlite3.connect(tmp_path/"catalog.sqlite3") as db:
        db.execute("CREATE TABLE crawler_assets (sha256 TEXT PRIMARY KEY,payload TEXT)")
        db.execute("INSERT INTO crawler_assets VALUES (?,?)",(sha,json.dumps({"path":str(image)})))
    assert run(tmp_path,analyzer=lambda *a:sample_v2())["success"] == 1
    assert run(tmp_path,analyzer=lambda *a:sample())["processed"] == 0


def sample_v2():
    return {**sample(),"content_type":"finished","nail_part":"hand",
            "design_visibility":"clear","style_evidence":{"法式":"甲尖分区"}}

def test_v2_content_rules():
    from nail_media.tag_schema import TagsV2
    good = TagsV2.model_validate(sample_v2()).result()
    assert good["recommendation_eligible"]
    process = TagsV2.model_validate({**sample_v2(),"content_type":"process"}).result()
    assert not process["recommendation_eligible"] and not process["styles"]
    conflict = TagsV2.model_validate({**sample_v2(),"styles":["纯色","渐变"]}).result()
    assert conflict["need_review"] and not conflict["recommendation_eligible"]
    missing = TagsV2.model_validate({**sample_v2(),"style_evidence":{}}).result()
    assert missing["need_review"]
    assert TagsV2.model_validate({**sample_v2(),"scenes":["婚礼"]}).result()["scenes"] == []
