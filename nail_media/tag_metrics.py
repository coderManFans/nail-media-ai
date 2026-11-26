import argparse
import json
import sqlite3
from pathlib import Path

def run(root):
    path=Path(root)/"catalog.sqlite3"
    with sqlite3.connect(path.resolve().as_uri()+"?mode=ro",uri=True) as db:
        rows=db.execute("""SELECT json_extract(j.value,'$.model'),COUNT(*),
            ROUND(AVG(json_extract(j.value,'$.seconds')),3),
            ROUND(SUM(json_extract(j.value,'$.seconds')),3)
            FROM image_tags t,json_each(t.payload,'$.model_attempts') j
            GROUP BY json_extract(j.value,'$.model')""").fetchall()
    return [{"model":m,"calls":n,"avg_seconds":a,"total_seconds":s} for m,n,a,s in rows]

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",default="runtime/media-library")
    print(json.dumps(run(p.parse_args().root),indent=2))
