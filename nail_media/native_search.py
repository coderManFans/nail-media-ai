"""Public search page collection, subject to site permission and robots rules."""
from urllib.parse import urlencode, urlsplit
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from .collectors import Media

BASE = "https://image.baidu.com"
AGENT = "NailMediaAI"

def search_url(keyword):
    return BASE + "/search/index?" + urlencode({"tn":"baiduimage","word":keyword})

def check_permission(client,url):
    response = client.get(BASE+"/robots.txt",follow_redirects=False)
    response.raise_for_status()
    robots = RobotFileParser()
    robots.parse(response.text.splitlines())
    if not robots.can_fetch(AGENT,url):
        raise PermissionError("Search path disallowed by robots.txt")

def parse_page(html,limit):
    soup = BeautifulSoup(html,"html.parser")
    items = []
    seen = set()
    for img in soup.select("img"):
        url = img.get("data-src") or img.get("src") or ""
        if url.startswith("//"):
            url = "https:"+url
        if url in seen or not url.startswith("https://"):
            continue
        # Only explicit result elements, not logos or navigation images.
        if not img.find_parent(class_="imgitem"):
            continue
        item = Media(BASE+"/",url,"baidu",title=img.get("alt",""))
        try:
            item.record()
        except ValueError:
            continue
        seen.add(url)
        items.append(item)
        if len(items)>=limit:
            break
    return items

class NativeBaiduSearch:
    def __init__(self,client,browser=False):
        self.client,self.browser=client,browser
    def search(self,keyword,limit):
        url=search_url(keyword)
        check_permission(self.client,url)
        if self.browser:
            from .browser_engine import render
            html=render(url)
        else:
            response=self.client.get(url,follow_redirects=False)
            response.raise_for_status()
            html=response.text
        items=parse_page(html,limit)
        print("Native Baidu result count:",len(items),flush=True)
        return items
