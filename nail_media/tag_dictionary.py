"""Editable presentation dictionary; canonical AI values remain stable."""
import sqlite3
from contextlib import closing
from .tag_schema import TagsV2

FIELDS=("colors","styles","nail_shape")
def defaults():
    props=TagsV2.model_json_schema()["properties"]
    return [(field,value,value,1,1) for field in FIELDS for value in props[field].get("items",props[field])["enum"]]

def initialize(db):
    db.execute("CREATE TABLE IF NOT EXISTS tag_dictionary (category TEXT, code TEXT, label TEXT NOT NULL, enabled INTEGER NOT NULL, builtin INTEGER NOT NULL, PRIMARY KEY(category,code), UNIQUE(category,label))")
    db.executemany("INSERT OR IGNORE INTO tag_dictionary VALUES (?,?,?,?,?)",defaults())

def list_tags(path):
    with closing(sqlite3.connect(path)) as db:
        with db:
            initialize(db)
            return [dict(zip(("category","code","label","enabled","builtin"),r)) for r in db.execute("SELECT * FROM tag_dictionary ORDER BY category,builtin DESC,code")]

def change(path,category,code,label=None,enabled=True,operation="update"):
    if category not in FIELDS or not code.strip() or len(code)>80:
        raise ValueError("Invalid category or code")
    if operation!="delete" and (not label or not label.strip() or len(label)>80):
        raise ValueError("Invalid label")
    with closing(sqlite3.connect(path)) as db:
        with db:
            initialize(db)
            row=db.execute("SELECT builtin FROM tag_dictionary WHERE category=? AND code=?",(category,code)).fetchone()
            if operation=="create":
                db.execute("INSERT INTO tag_dictionary VALUES (?,?,?,?,0)",(category,code,label.strip(),int(enabled)))
            elif not row:
                raise KeyError(code)
            elif operation=="delete":
                if row[0]:
                    db.execute("UPDATE tag_dictionary SET enabled=0 WHERE category=? AND code=?",(category,code))
                else:
                    db.execute("DELETE FROM tag_dictionary WHERE category=? AND code=?",(category,code))
            else:
                db.execute("UPDATE tag_dictionary SET label=?,enabled=? WHERE category=? AND code=?",(label.strip(),int(enabled),category,code))
    return list_tags(path)
