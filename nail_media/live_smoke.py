"""Run one live search and report the actual outcome without starting a scheduler."""
import argparse
import json
from pathlib import Path
import httpx
from .catalog import Catalog
from .native_search import NativeBaiduSearch
from .commons import CommonsCollector
from .pipeline import run_task

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform",choices=["baidu","commons"],default="baidu")
    parser.add_argument("--keyword")
    parser.add_argument("--mode",choices=["http","browser"],default="http")
    parser.add_argument("--limit",type=int,choices=range(1,6),default=3)
    parser.add_argument("--root",default="runtime/live-smoke")
    parser.add_argument("--approved",help="JSON array of explicitly approved image URLs")
    parser.add_argument("--media-host",action="append",default=[])
    args=parser.parse_args()
    root=Path(args.root)
    approved=json.loads(Path(args.approved).read_text()) if args.approved else []
    if not isinstance(approved,list) or not all(isinstance(x,str) for x in approved):
        parser.error("--approved must contain a JSON array of URLs")
    keyword=args.keyword or ("猫眼美甲" if args.platform=="baidu" else "nail art")
    task={"id":"live-"+args.platform,"platform":args.platform,"keyword":keyword,"limit":args.limit}
    with httpx.Client(timeout=30,headers={"User-Agent":"NailMediaAI/0.1 (https://github.com/coderManFans/nail-media-ai)"}) as client:
        provider=NativeBaiduSearch(client,browser=args.mode=="browser") if args.platform=="baidu" else CommonsCollector(client)
        report=run_task(task,{args.platform:provider},Catalog(root/"catalog.sqlite3"),client,root,set(approved),tuple(["upload.wikimedia.org"]+args.media_host))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report["status"]=="blocked":
        print("Search blocked by access policy.")
    print("History:",root/"history.jsonl")
    return 0 if report["status"]=="success" and report["found"]>0 else 1

if __name__=="__main__":
    raise SystemExit(main())
