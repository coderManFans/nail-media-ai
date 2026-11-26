"""Single-host, checkpointed production pipeline."""
import argparse
import fcntl
import json
import sqlite3
import time
from pathlib import Path
from . import orchestrator, video_frames, cluster_pipeline, tag_pipeline, tag_review, recommendation
from .catalog import Catalog
from .task_store import TaskStore
from .sync import sync

def validate(root):
    with sqlite3.connect(root/"catalog.sqlite3") as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        checks=[
            ("video_frames","crawler_assets","image_sha","sha256"),
            ("video_frames","video_assets","video_sha","sha256"),
            ("image_tags","crawler_assets","image_sha","sha256"),
            ("image_cluster_members","image_clusters","cluster_id","cluster_id"),
            ("image_cluster_members","crawler_assets","image_sha","sha256"),
        ]
        errors=[]
        for child,parent,fk,pk in checks:
            if child in tables:
                if parent not in tables:
                    errors.append(child+":missing_parent")
                elif db.execute(f"SELECT COUNT(*) FROM {child} c LEFT JOIN {parent} p ON c.{fk}=p.{pk} WHERE p.{pk} IS NULL").fetchone()[0]:
                    errors.append(child+":orphan:"+fk)
        return {"errors":errors}

def execute(root, stages, *, resume=False, identity="default"):
    root=Path(root)
    root.mkdir(parents=True,exist_ok=True)
    with (root/"production.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with sqlite3.connect(root/"production.sqlite3") as db:
            db.execute("CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, identity TEXT, state TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS steps (run_id INTEGER, name TEXT, state TEXT, payload TEXT, seconds REAL, PRIMARY KEY(run_id,name))")
            if resume:
                row=db.execute("SELECT id,identity FROM runs WHERE state NOT IN ('success','success_with_warnings') ORDER BY id DESC LIMIT 1").fetchone()
                if not row or row[1]!=identity:
                    raise ValueError("No compatible unfinished run")
                run_id=row[0]
            else:
                run_id=db.execute("INSERT INTO runs(identity,state) VALUES (?,'running')",(identity,)).lastrowid
            db.execute("UPDATE runs SET state='running' WHERE id=?",(run_id,))
            db.commit()
            for name,fn in stages:
                row=db.execute("SELECT state FROM steps WHERE run_id=? AND name=?",(run_id,name)).fetchone()
                if row and row[0] in ("success","warning"):
                    continue
                start=time.monotonic()
                try:
                    result=fn()
                    failed=bool(result.get("errors") or result.get("failed"))
                except Exception as exc:
                    result={"error":type(exc).__name__}
                    failed=True
                soft = name=="review" and failed and "error" not in result and bool(result.get("failed"))
                state="warning" if soft else ("failed" if failed else "success")
                with db:
                    db.execute("INSERT OR REPLACE INTO steps VALUES (?,?,?,?,?)",(run_id,name,state,json.dumps(result,ensure_ascii=False),round(time.monotonic()-start,3)))
                    if failed and not soft:
                        db.execute("UPDATE runs SET state='failed' WHERE id=?",(run_id,))
                if failed and not soft:
                    return {"run_id":run_id,"state":"failed","stage":name,"result":result}
            warnings=[r[0] for r in db.execute("SELECT name FROM steps WHERE run_id=? AND state='warning'",(run_id,))]
            final_state="success_with_warnings" if warnings else "success"
            with db:
                db.execute("UPDATE runs SET state=? WHERE id=?",(final_state,run_id))
            return {"run_id":run_id,"state":final_state,"warnings":warnings}

def status(root):
    path=Path(root)/"production.sqlite3"
    if not path.exists():
        return {"runs":[],"steps":[]}
    with sqlite3.connect(path) as db:
        db.row_factory=sqlite3.Row
        return {"runs":[dict(r) for r in db.execute("SELECT * FROM runs ORDER BY id DESC LIMIT 10")],
                "steps":[dict(r) for r in db.execute("SELECT * FROM steps WHERE run_id=(SELECT MAX(id) FROM runs) ORDER BY rowid")]}

def build(path, authorized=False, private=False):
    path=Path(path).resolve()
    cfg=json.loads(path.read_text())
    root,tasks=orchestrator.load_config(path.parent/cfg["collection_config"])
    model=cfg["model"]
    backup=cfg["fallback_model"]
    stages=[]
    if cfg.get("collect"):
        if not authorized:
            raise PermissionError("Confirm collection authorization")
        def collect():
            store=TaskStore(root/"collection-tasks.sqlite3")
            store.register(tasks)
            store.recover()
            results=orchestrator.run_cycle(tasks,root,store)
            return {"results":results,"errors":[r["id"] for r in results if r["status"] not in ("success","empty_or_filtered")]}
        stages.append(("collection",collect))
    def initialize():
        Catalog(root/"catalog.sqlite3")
        return {}
    stages.extend([
        ("initialize",initialize),
        ("frames",lambda:video_frames.process(root,limit=cfg["video_limit"])),
        ("cluster",lambda:cluster_pipeline.run(root)),
        ("primary_tags",lambda:tag_pipeline.run(root,model=model,limit=cfg["tag_limit"],representatives_only=True)),
        ("review",lambda:tag_review.run(root,model,backup,limit=cfg["review_limit"])),
        ("recommendation",lambda:recommendation.run(root)),
        ("validate",lambda:validate(root)),
        ("export",lambda:{"records":Catalog(root/"catalog.sqlite3").export(root/"catalog.jsonl")}),
    ])
    if cfg.get("sync_checkout"):
        if not private:
            raise PermissionError("Confirm private archive authorization")
        stages.append(("sync",lambda:{"records":sync(root/"catalog.sqlite3",path.parent/cfg["sync_checkout"],confirmed=True)}))
    return root,stages,cfg

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default="config/production.json")
    modes=p.add_mutually_exclusive_group(required=True)
    for mode in ("once","resume","status","daemon"):
        modes.add_argument("--"+mode,action="store_true")
    p.add_argument("--confirm-authorized",action="store_true")
    p.add_argument("--confirm-authorized-private",action="store_true")
    a=p.parse_args()
    if a.status:
        path=Path(a.config).resolve()
        cfg=json.loads(path.read_text())
        root,_=orchestrator.load_config(path.parent/cfg["collection_config"])
        print(json.dumps(status(root),ensure_ascii=False,indent=2))
        return 0
    root,stages,cfg=build(a.config,a.confirm_authorized,a.confirm_authorized_private)
    identity=json.dumps(cfg,sort_keys=True)
    while True:
        result=execute(root,stages,resume=a.resume,identity=identity)
        print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
        if not a.daemon or result["state"] not in ("success","success_with_warnings"):
            return int(result["state"]!="success")
        time.sleep(max(60,cfg.get("interval_seconds",3600)))

if __name__=="__main__":
    raise SystemExit(main())
