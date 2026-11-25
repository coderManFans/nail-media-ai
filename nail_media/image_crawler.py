"""Reusable image extraction and conservative per-origin request pacing."""
import time
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from .collectors import Media

class RateLimiter:
    def __init__(self, interval=5, clock=time.monotonic, sleep=time.sleep):
        self.interval=max(5,interval)
        self.clock,self.sleep=clock,sleep
        self.last={}
    def wait(self,url):
        origin=urlsplit(url).hostname
        if origin in self.last:
            delay=self.interval-(self.clock()-self.last[origin])
            if delay>0:
                self.sleep(delay)
        self.last[origin]=self.clock()

def extract_images(html,source_url,platform,limit=20,selector="img"):
    if not 1<=limit<=20:
        raise ValueError("limit must be 1..20")
    items=[]
    seen=set()
    for img in BeautifulSoup(html,"html.parser").select(selector):
        raw=img.get("data-src") or img.get("data-original") or img.get("src")
        if not isinstance(raw,str) or not raw.strip():
            continue
        url=urljoin(source_url,raw)
        if url in seen:
            continue
        item=Media(source_url,url,platform,title=img.get("alt",""))
        try:
            item.record()
        except ValueError:
            continue
        seen.add(url)
        items.append(item)
        if len(items)==limit:
            break
    return items
