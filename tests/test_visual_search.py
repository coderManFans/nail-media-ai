import json
import sqlite3
import numpy as np
import pytest
from nail_media.visual_search import normalize,search

def test_normalize():
    assert np.allclose(normalize([3,4]),[.6,.8])
    with pytest.raises(ValueError):
        normalize([0,0])

def test_search(tmp_path):
    with sqlite3.connect(tmp_path/"catalog.sqlite3") as db:
        db.executescript("""
        CREATE TABLE crawler_assets(sha256 TEXT);
        CREATE TABLE image_clusters(representative_sha TEXT);
        CREATE TABLE image_tags(image_sha TEXT,model TEXT,version TEXT,payload TEXT);
        CREATE TABLE image_vectors(image_sha TEXT,encoder TEXT,dimension INTEGER,vector BLOB);
        """)
        for sha,vec,color in [("a",[1,0],"红色"),("b",[0,1],"蓝色")]:
            db.execute("INSERT INTO crawler_assets VALUES (?)",(sha,))
            db.execute("INSERT INTO image_clusters VALUES (?)",(sha,))
            db.execute("INSERT INTO image_tags VALUES (?,?,?,?)",(sha,"qwen2.5vl:7b","v2",json.dumps({"recommendation_eligible":True,"colors":[color]})))
            db.execute("INSERT INTO image_vectors VALUES (?,?,?,?)",(sha,"fake",2,normalize(vec).tobytes()))
    assert search(tmp_path,"fake",[1,0])[0]["image_sha"]=="a"
    assert search(tmp_path,"fake",[1,0],color="蓝色")[0]["image_sha"]=="b"
