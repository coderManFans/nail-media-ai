import argparse
import json
import sqlite3
from pathlib import Path

VERSION="v1"
def recommend(tags):
    if not tags.get("recommendation_eligible"):
        return {"scenes":[],"seasons":[],"evidence":[]}
    colors=set(tags.get("colors",[]))
    styles=set(tags.get("styles",[]))
    scenes=set()
    seasons=set()
    evidence=[]
    for field,values,targets,reason in [
        ("scenes",{"裸粉色","奶茶色","奶白色"},{"通勤","日常"},"柔和中性色"),
        ("scenes",{"碎钻","珍珠"},{"婚礼","聚会"},"装饰性款式"),
        ("seasons",{"粉色","裸粉色","抹茶绿"},{"春季"},"柔和春季配色"),
        ("seasons",{"蓝色","白色","透明"},{"夏季"},"清爽配色"),
        ("seasons",{"焦糖棕","奶茶色"},{"秋季"},"暖棕配色"),
        ("seasons",{"酒红色","银色"},{"冬季"},"深色或银色配色")]:
        matched=values & (colors|styles)
        if matched:
            (scenes if field=="scenes" else seasons).update(targets)
            evidence.append({"rule":reason,"matched":sorted(matched),"suggestions":sorted(targets)})
    return {"scenes":sorted(scenes),"seasons":sorted(seasons),"evidence":evidence}

def run(root):
    path=Path(root)/"catalog.sqlite3"
    if not path.is_file():
        raise FileNotFoundError(path)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS image_recommendations (image_sha TEXT,model TEXT,tag_version TEXT,rule_version TEXT,payload TEXT,PRIMARY KEY(image_sha,model,tag_version,rule_version))")
        rows=db.execute("SELECT image_sha,model,version,payload FROM image_tags WHERE version='v2' OR version LIKE 'v2:routed:%'").fetchall()
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='manual_tags' AND type='table'").fetchone():
            manual=dict(db.execute("SELECT image_sha,payload FROM manual_tags"))
            for sha in manual:
                db.execute("DELETE FROM image_recommendations WHERE image_sha=?",(sha,))
            rows=[r for r in rows if r[0] not in manual]+[(sha,"manual","v2",payload) for sha,payload in manual.items()]
        for sha,model,version,payload in rows:
            db.execute("INSERT OR REPLACE INTO image_recommendations VALUES (?,?,?,?,?)",(sha,model,version,VERSION,json.dumps(recommend(json.loads(payload)),ensure_ascii=False)))
    return {"processed":len(rows)}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default="runtime/media-library")
    print(json.dumps(run(p.parse_args().root)))
