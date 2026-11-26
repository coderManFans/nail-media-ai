from dataclasses import dataclass, asdict
from hashlib import sha256
from urllib.parse import urlsplit, urljoin, parse_qsl
from typing import Protocol
import re

# Only simple, non-secret image transformation parameters are retained.
PUBLIC_IMAGE_PARAMS = {"w", "h", "width", "height", "q", "quality", "format", "fm", "fit", "resize", "size", "type", "f", "s"}
def safe_image_query(query):
    try:
        pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True, max_num_fields=20)
        return bool(pairs) and all(k.lower() in PUBLIC_IMAGE_PARAMS and re.fullmatch(r"[a-zA-Z0-9_,.-]{1,40}", v) for k,v in pairs)
    except ValueError:
        return False

from bs4 import BeautifulSoup

@dataclass(frozen=True)
class Media:
    source_url: str
    media_url: str
    platform: str
    media_type: str = "image"
    title: str = ""
    license_status: str = "unknown"

    def record(self):
        for url in (self.source_url, self.media_url):
            p = urlsplit(url)
            if p.scheme != "https" or not p.hostname or p.username or p.password or p.fragment or (p.query and not (url == self.media_url and self.media_type == "image" and safe_image_query(p.query))):
                raise ValueError("Expected HTTPS URL without credentials, query or fragment")
        if self.media_type not in {"image", "video", "post"}:
            raise ValueError("Unsupported media type")
        return {"id": sha256((self.platform + "\n" + self.media_url).encode()).hexdigest(), **asdict(self)}

class Collector(Protocol):
    def collect(self, payload: str, source_url: str) -> list[Media]: ...

class HtmlCollector:
    """Parse supplied HTML from an authorized source; no network access."""
    def collect(self, payload: str, source_url: str) -> list[Media]:
        result = []
        for img in BeautifulSoup(payload, "html.parser").select("img[src]"):
            item = Media(source_url, urljoin(source_url, img["src"]), "generic", title=img.get("alt", ""))
            try:
                item.record()
            except ValueError:
                continue
            result.append(item)
        return result

def platform_for(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower()
    for name, domains in {"baidu": ["baidu.com"], "xiaohongshu": ["xiaohongshu.com", "xhslink.com"], "douyin": ["douyin.com", "iesdouyin.com"], "tiktok": ["tiktok.com"]}.items():
        if any(host == d or host.endswith("." + d) for d in domains):
            return name
    return "generic"

class ManifestCollector:
    def collect(self, payload: str, source_url: str = "") -> list[Media]:
        import json
        return [Media(source_url=i["source_url"], media_url=i.get("media_url", i["source_url"]), platform=platform_for(i["source_url"]), media_type=i.get("media_type", "image"), title=i.get("title", "")) for i in json.loads(payload)]
