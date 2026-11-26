from nail_media.tag_review import eligible
from nail_media.recommendation import recommend

def test_review_selection():
    assert eligible("failed",{})
    assert eligible("review",{"content_type":"finished"})
    assert not eligible("review",{"content_type":"process"})
    assert eligible("review",{"content_type":"process","review_reasons":["content_type_conflict"]})

def test_recommendation():
    tags={"recommendation_eligible":True,"colors":["裸粉色"],"styles":["珍珠"]}
    result=recommend(tags)
    assert "春季" in result["seasons"] and "婚礼" in result["scenes"]
    assert recommend({**tags,"recommendation_eligible":False})["scenes"]==[]
