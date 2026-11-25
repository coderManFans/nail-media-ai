"""Public search page collection, subject to site permission and robots rules."""
from urllib.parse import urlencode, urlsplit
from urllib.robotparser import RobotFileParser
from bs4 import BeautifulSoup
from .collectors import Media
from .image_crawler import RateLimiter, extract_images

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
    return extract_images(html,BASE+"/","baidu",min(limit,20),".imgitem img")

class NativeBaiduSearch:
    def __init__(self,client,browser=False):
        self.client,self.browser=client,browser
        self.limiter=RateLimiter()
    def search(self,keyword,limit):
        url=search_url(keyword)
        self.limiter.wait(url)
        check_permission(self.client,url)
        self.limiter.wait(url)
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
