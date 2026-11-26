"""Explicitly enabled local job runner; fixed commands, no shell."""
import json
import subprocess
import sys
import time
from pathlib import Path
from threading import Lock
import fcntl

class Jobs:
    def __init__(self,root):
        self.root=Path(root).resolve()
        self.guard=Lock()
        self.process=None
    def start(self,kind,limit,authorized=False):
        if not 1<=limit<=100:
            raise ValueError("Invalid limit")
        args={
            "index":["nail_media.visual_search","--root",str(self.root),"--index","--limit",str(limit)],
            "tags":["nail_media.tag_pipeline","--root",str(self.root),"--representatives-only","--limit",str(limit)],
            "review":["nail_media.tag_review","--root",str(self.root),"--limit",str(limit)],
            "recommend":["nail_media.recommendation","--root",str(self.root)],
        }
        if kind in ("pipeline","resume"):
            from .production_pipeline import build
            config=Path("config/production.json").resolve()
            root,_,_=build(config,authorized=authorized,private=False)
            if root!=self.root:
                raise ValueError("Pipeline root mismatch")
            args[kind]=["nail_media.production_pipeline","--config",str(config),"--once" if kind=="pipeline" else "--resume"]
            if authorized:
                args[kind].append("--confirm-authorized")
        if kind not in args:
            raise ValueError("Unsupported job")
        with self.guard:
            if self.process is not None and self.process.poll() is None:
                raise BlockingIOError('Job running')
            self.root.mkdir(parents=True,exist_ok=True)
            with (self.root/"production.lock").open("a") as lock:
                fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
                if kind in ("pipeline","resume"):
                    fcntl.flock(lock,fcntl.LOCK_UN)
                with (self.root/"local-job.log").open("w") as log:
                    self.process=subprocess.Popen([sys.executable,"-m",*args[kind]],stdout=log,stderr=subprocess.STDOUT,pass_fds=() if kind in ('pipeline','resume') else (lock.fileno(),))
            (self.root/"local-job.json").write_text(json.dumps({"kind":kind,"pid":self.process.pid,"started":time.time()}))
            return self.status()
    def status(self):
        meta=self.root/"local-job.json"
        result=json.loads(meta.read_text()) if meta.exists() else {}
        if self.process is not None:
            code=self.process.poll()
            result.update(state="running" if code is None else ("success" if code==0 else "failed"),exit_code=code)
        else:
            result["state"]="unknown" if result else "idle"
        log=self.root/"local-job.log"
        if log.exists():
            with log.open("rb") as fp:
                fp.seek(max(0,log.stat().st_size-16000))
                result["log"]=fp.read().decode("utf-8",errors="replace")
        return result
