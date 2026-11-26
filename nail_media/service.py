import argparse
import json
import os
import time
from pathlib import Path
import httpx
from .catalog import Catalog
from .task_store import TaskStore
from .commons import CommonsCollector
from .providers import ConfiguredSearch
from .pipeline import run_task
from .baidu import ApiHzSearch, FallbackSearch
from .native_search import NativeBaiduSearch
from .icrawler_engine import run_icrawler_task

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tasks",default="runtime/tasks.json")
    p.add_argument("--root",default="runtime")
    p.add_argument("--once",action="store_true")
    p.add_argument("--approved",help="JSON array of explicitly authorized direct media URLs")
    p.add_argument("--media-host",action="append",default=[],help="Explicitly approved media hostname; repeat as needed")
    p.add_argument("--baidu-engine",choices=["icrawler","legacy"],default="icrawler")
    p.add_argument("--status",action="store_true")
    p.add_argument("--reset-task",help="Reset a failed or interrupted task; stop other workers first")
    a = p.parse_args()
    root = Path(a.root)
    tasks = json.loads(Path(a.tasks).read_text(encoding="utf-8"))
    approved = set(json.loads(Path(a.approved).read_text())) if a.approved else set()
    catalog = Catalog(root/"catalog.sqlite3")
    store = TaskStore(root/"tasks.sqlite3")
    store.register(tasks)
    if a.status:
        print(json.dumps(store.rows(),ensure_ascii=False,indent=2))
        return
    if a.reset_task:
        print("Reset tasks:",store.reset(a.reset_task))
        return
    with httpx.Client(timeout=20,headers={"User-Agent":"NailMediaAI/0.1 ("+os.getenv("CRAWLER_CONTACT","https://github.com/coderManFans/nail-media-ai")+")"}) as client:
        providers = {"commons":CommonsCollector(client)}
        for platform in ("baidu","xiaohongshu","douyin"):
            endpoint = os.getenv(platform.upper()+"_SEARCH_URL")
            if endpoint:
                providers[platform] = ConfiguredSearch(client,endpoint,platform,os.getenv(platform.upper()+"_SEARCH_TOKEN"))
        native = os.getenv("BAIDU_NATIVE_MODE")
        if native in {"http","browser"}:
            providers["baidu"] = NativeBaiduSearch(client,browser=native=="browser")
        demo = os.getenv("APIHZ_PUBLIC_DEMO") == "1"
        user_id = os.getenv("APIHZ_ID") or ("88888888" if demo else "")
        key = os.getenv("APIHZ_KEY") or ("88888888" if demo else "")
        if user_id and key:
            api = ApiHzSearch(client,user_id,key)
            if "baidu" not in providers:
                providers["baidu"] = api
            elif os.getenv("APIHZ_ALLOW_FALLBACK") == "1":
                providers["baidu"] = FallbackSearch(providers["baidu"],api)
        while True:
            for task in tasks:
                if not task.get("enabled") or not store.claim(task["id"]):
                    continue
                if task["platform"]=="baidu" and a.baidu_engine=="icrawler":
                    report = run_icrawler_task(task,catalog,root)
                else:
                    report = run_task(task,providers,catalog,client,root,approved,tuple(["upload.wikimedia.org"]+a.media_host))
                print(json.dumps(report),flush=True)
                store.finish(task["id"],report["status"],task["interval_hours"])
                time.sleep(3)
            if a.once:
                break
            time.sleep(30)

if __name__ == "__main__":
    main()
