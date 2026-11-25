import httpx
import json
from urllib.parse import urlsplit
from .collectors import Media

class CommonsCollector:
    endpoint = "https://commons.wikimedia.org/w/api.php"
    def __init__(self, client):
        self.client = client
    def search(self, keyword, limit=20):
        if not 1 <= limit <= 50:
            raise ValueError("limit must be 1..50")
        response = self.client.get(self.endpoint, params={"action":"query","generator":"search","gsrsearch":keyword,"gsrnamespace":6,"gsrlimit":limit,"prop":"imageinfo","iiprop":"url|mime","format":"json","formatversion":2})
        print('Commons HTTP status:', response.status_code, flush=True)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise ValueError("Commons API returned an error")
        items = []
        stats = {'pages':len(data.get('query',{}).get('pages',[])), 'imageinfo':0,'non_image':0,'invalid_url':0,'query_or_fragment':0,'non_https':0}
        for page in data.get("query", {}).get("pages", []):
            for info in page.get("imageinfo", []):
                stats["imageinfo"] += 1
                if not info.get("mime", "").startswith("image/"):
                    stats["non_image"] += 1
                    continue
                item = Media(info["descriptionurl"], info["url"], "commons", title=page.get("title", ""))
                try:
                    item.record()
                except ValueError:
                    stats["invalid_url"] += 1
                    for url in (item.source_url,item.media_url):
                        try:
                            p = urlsplit(url)
                            stats["query_or_fragment"] += int(bool(p.query or p.fragment))
                            stats["non_https"] += int(p.scheme != "https")
                        except ValueError:
                            pass
                    continue
                items.append(item)
        print("Commons search diagnostics:",json.dumps({**stats,"accepted":len(items)}),flush=True)
        return items[:limit]

def collect(keyword, limit, contact):
    if not contact.strip():
        raise ValueError("Provide a contact for the API user agent")
    with httpx.Client(timeout=20, headers={"User-Agent":f"NailMediaAI/0.1 ({contact})"}) as client:
        return CommonsCollector(client).search(keyword, limit)
