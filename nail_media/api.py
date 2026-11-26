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

class JobInput(BaseModel):
    kind: Literal['index','tags','review','recommend']
    limit: int = Field(default=10,ge=1,le=100)

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
            return jobs.start(body.kind,body.limit)
        except BlockingIOError:
            raise HTTPException(409,'Another production job is running')
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
                items.append({"image_sha":sha,"width":asset.get("width"),"height":asset.get("height"),"status":status_value or "pending","tags":json.loads(tags) if tags else {}})
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
