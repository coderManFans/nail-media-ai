"""Local read-only media API. Bind to loopback unless protected by authentication."""
import os
import io
import json
import sqlite3
from pathlib import Path
from threading import Lock
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from PIL import Image
from .visual_search import Encoder, search, DEFAULT_MODEL, DEFAULT_WEIGHTS
from .production_pipeline import status
from .local_jobs import Jobs
from fastapi import Request
from pydantic import BaseModel, Field
from typing import Literal
from .tag_schema import TagsV2
from pydantic import ValidationError
import fcntl

class JobInput(BaseModel):
    kind: Literal['index','tags','review','recommend','pipeline','resume']
    limit: int = Field(default=10,ge=1,le=100)
    authorized: bool = False

class CollectionEdit(BaseModel):
    id: str
    keyword: str = Field(max_length=200)
    limit: int = Field(ge=1,le=20)
    interval_hours: int = Field(ge=1,le=8760)
    enabled: bool

def create_app(root=None):
    root=Path(root or os.environ.get("NAIL_MEDIA_ROOT","runtime/media-library")).resolve()
    app=FastAPI(title="Nail Media AI")
    lock=Lock()
    jobs=Jobs(root)
    @app.get('/api/jobs')
    def job_status():
        return jobs.status()
    @app.post('/api/jobs')
    def start_job(body:JobInput, request:Request):
        if os.environ.get('NAIL_MEDIA_ENABLE_WRITES')!='1' or request.headers.get('origin') not in ('http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8000'):
            raise HTTPException(403,'Local writes disabled or invalid origin')
        try:
            return jobs.start(body.kind,body.limit,body.authorized)
        except BlockingIOError:
            raise HTTPException(409,'Another production job is running')
        except (ValueError,PermissionError) as exc:
            raise HTTPException(400,str(exc))
    @app.put('/api/assets/{sha}/review')
    def manual_review(sha:str, body:TagsV2, request:Request):
        if os.environ.get('NAIL_MEDIA_ENABLE_WRITES')!='1' or request.headers.get('origin') not in ('http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8000'):
            raise HTTPException(403,'Local writes disabled or invalid origin')
        result=body.result()
        try:
            with (root/'production.lock').open('a') as guard:
                fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
                with sqlite3.connect(root/'catalog.sqlite3') as conn:
                    if not conn.execute('SELECT 1 FROM crawler_assets WHERE sha256=?',(sha,)).fetchone():
                        raise HTTPException(404,'Asset not found')
                    conn.execute('CREATE TABLE IF NOT EXISTS manual_tags (image_sha TEXT PRIMARY KEY,payload TEXT NOT NULL,updated_at TEXT DEFAULT CURRENT_TIMESTAMP)')
                    conn.execute('INSERT OR REPLACE INTO manual_tags(image_sha,payload) VALUES (?,?)',(sha,json.dumps(result,ensure_ascii=False)))
        except BlockingIOError:
            raise HTTPException(409,'Production job running')
        return result
    @app.get('/api/collection')
    def collection():
        cfg=json.loads(Path('config/collection.json').read_text())
        return [{k:t.get(k) for k in ('id','platform','keyword','limit','interval_hours','enabled','mode')} for t in cfg['tasks']]
    @app.put('/api/collection')
    def update_collection(body:list[CollectionEdit],request:Request):
        if os.environ.get('NAIL_MEDIA_ENABLE_WRITES')!='1' or request.headers.get('origin') not in ('http://127.0.0.1:5173','http://localhost:5173','http://127.0.0.1:8000'):
            raise HTTPException(403,'Local writes disabled or invalid origin')
        path=Path('config/collection.json')
        root.mkdir(parents=True,exist_ok=True)
        try:
            with (root/'production.lock').open('a') as guard:
                fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
                cfg=json.loads(path.read_text())
                edits={t.id:t for t in body}
                if len(edits)!=len(body) or set(edits)!={t['id'] for t in cfg['tasks']}:
                    raise HTTPException(422,'Task IDs must match existing configuration')
                for task in cfg['tasks']:
                    task.update(edits[task['id']].model_dump(exclude={'id'}))
                temp=path.with_suffix('.tmp')
                temp.write_text(json.dumps(cfg,ensure_ascii=False,indent=2))
                temp.replace(path)
        except BlockingIOError:
            raise HTTPException(409,'Production job running')
        return collection()
    @app.get('/api/tag-schema')
    def tag_schema():
        return TagsV2.model_json_schema()
    encoder=None
    identity=DEFAULT_MODEL+":"+DEFAULT_WEIGHTS+":v1"
    def get_encoder():
        nonlocal encoder
        if encoder is None:
            encoder=Encoder()
        return encoder
    def db():
        path=root/"catalog.sqlite3"
        if not path.is_file():
            raise HTTPException(503,"Catalog not initialized")
        return sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)
    @app.get("/api/health")
    def health():
        return {"ready":(root/"catalog.sqlite3").is_file()}
    @app.get("/api/statistics")
    def statistics():
        with db() as conn:
            tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            return {t:conn.execute("SELECT COUNT(*) FROM "+t).fetchone()[0] if t in tables else 0 for t in ("crawler_assets","video_assets","image_clusters","image_tags","image_vectors","tag_review_queue")}
    @app.get("/api/assets")
    def assets(limit:int=Query(24,ge=1,le=100),offset:int=Query(0,ge=0),state:str=""):
        with db() as conn:
            tables={r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "crawler_assets" not in tables:
                return {"total":0,"items":[]}
            join=" LEFT JOIN image_tags t ON t.image_sha=a.sha256 AND t.model='qwen2.5vl:7b' AND t.version='v2'" if "image_tags" in tables else ""
            where=" WHERE t.status=?" if state and join else ""
            args=(state,) if where else ()
            base=" FROM crawler_assets a"+join+where
            total=conn.execute("SELECT COUNT(*)"+base,args).fetchone()[0]
            rows=conn.execute("SELECT a.sha256,a.payload,"+("t.status,t.payload" if join else "NULL,NULL")+base+" ORDER BY a.sha256 LIMIT ? OFFSET ?",(*args,limit,offset))
            items=[]
            for sha,raw,status_value,tags in rows:
                asset=json.loads(raw)
                manual=conn.execute("SELECT payload FROM manual_tags WHERE image_sha=?",(sha,)).fetchone() if "manual_tags" in tables else None
                if manual:
                    tags=manual[0]
                items.append({"image_sha":sha,"width":asset.get("width"),"height":asset.get("height"),"status":"manual" if manual else (status_value or "pending"),"tags":json.loads(tags) if tags else {}})
            return {"total":total,"items":items}
    @app.get("/api/reviews")
    def reviews(limit:int=Query(100,ge=1,le=100),offset:int=Query(0,ge=0)):
        with db() as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='tag_review_queue'").fetchone():
                return []
            return [{"image_sha":sha,"primary_model":primary,"backup_model":backup,"state":state,"detail":json.loads(raw)} for sha,primary,backup,state,raw in conn.execute("SELECT image_sha,primary_model,backup_model,state,payload FROM tag_review_queue ORDER BY image_sha LIMIT ? OFFSET ?",(limit,offset))]
    @app.get("/api/pipeline")
    def pipeline():
        return status(root)
    @app.get("/api/images/{sha}")
    def image(sha:str):
        with db() as conn:
            row=conn.execute("SELECT payload FROM crawler_assets WHERE sha256=?",(sha,)).fetchone()
        if not row:
            raise HTTPException(404,"Image not found")
        path=root/"images"/Path(json.loads(row[0])["path"]).name
        if path.is_symlink() or not path.is_file():
            raise HTTPException(404,"Image not found")
        return FileResponse(path)
    def retrieve(query,limit,color,style,shape,include_unreviewed):
        try:
            return search(root,identity,query,limit=limit,color=color,style=style,shape=shape,eligible_only=not include_unreviewed)
        except sqlite3.OperationalError:
            raise HTTPException(503,"Search index not initialized")
    @app.get("/api/search")
    def text_search(q:str=Query("",max_length=300),limit:int=Query(20,ge=1,le=100),color:str|None=None,style:str|None=None,shape:str|None=None,include_unreviewed:bool=False):
        query=None
        if q.strip():
            with lock:
                query=get_encoder().text(q)
        return retrieve(query,limit,color,style,shape,include_unreviewed)
    @app.post("/api/search/image")
    def image_search(file:UploadFile=File(...),limit:int=Query(20,ge=1,le=100)):
        raw=file.file.read(10*1024*1024+1)
        if len(raw)>10*1024*1024:
            raise HTTPException(413,"Image too large")
        try:
            with Image.open(io.BytesIO(raw)) as img:
                if img.width*img.height>25_000_000 or img.format not in ("JPEG","PNG","WEBP"):
                    raise ValueError("Invalid image")
                img.load()
                with lock:
                    query=get_encoder().image(img)
        except (ValueError,OSError,Image.DecompressionBombError):
            raise HTTPException(400,"Invalid image")
        return retrieve(query,limit,None,None,None,False)
    return app

app=create_app()
