"""Independent single-worker icrawler smoke test; run on permitted sources."""
import argparse
import logging
from importlib.metadata import version
from pathlib import Path
from tempfile import mkdtemp
from PIL import Image
from icrawler.builtin import BaiduImageCrawler

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--keyword",default="猫眼美甲")
    p.add_argument("--limit",type=int,choices=range(1,6),default=3)
    args=p.parse_args()
    base=Path("runtime/icrawler-smoke")
    base.mkdir(parents=True,exist_ok=True)
    root=Path(mkdtemp(prefix="run-",dir=base))
    print("icrawler version:",version("icrawler"),flush=True)
    print("Output:",root,flush=True)
    crawler=BaiduImageCrawler(feeder_threads=1,parser_threads=1,downloader_threads=1,storage={"root_dir":str(root)},log_level=logging.DEBUG)
    crawler.crawl(keyword=args.keyword,max_num=args.limit,min_size=(200,200))
    valid=0
    for path in sorted(root.iterdir()):
        if not path.is_file(): continue
        try:
            with Image.open(path) as im:
                width,height=im.size
                im.verify()
            if min(width,height)>=200:
                valid+=1
                print(f"VALID {path.name} {width}x{height} {path.stat().st_size} bytes")
        except Exception as exc:
            print(f"INVALID {path.name}: {type(exc).__name__}")
    print(f"RESULT valid_images={valid} requested={args.limit}",flush=True)
    return 0 if valid else 1

if __name__=="__main__":
    raise SystemExit(main())
