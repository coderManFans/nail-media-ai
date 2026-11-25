import httpx
from .collectors import Media

class CommonsCollector:
    endpoint = "https://commons.wikimedia.org/w/api.php"
    def __init__(self, client):
        self.client = client
    def search(self, keyword, limit=20):
        if not 1 <= limit <= 50:
            raise ValueError("limit must be 1..50")
        response = self.client.get(self.endpoint, params={"action":"query","generator":"search","gsrsearch":keyword,"gsrnamespace":6,"gsrlimit":limit,"prop":"imageinfo","iiprop":"url|mime","format":"json","formatversion":2})
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise ValueError("Commons API returned an error")
        items = []
        for page in data.get("query", {}).get("pages", []):
            for info in page.get("imageinfo", []):
                if not info.get("mime", "").startswith("image/"):
                    continue
                item = Media(info["descriptionurl"], info["url"], "commons", title=page.get("title", ""))
                try:
                    item.record()
                except ValueError:
                    continue
                items.append(item)
        return items[:limit]

def collect(keyword, limit, contact):
    if not contact.strip():
        raise ValueError("Provide a contact for the API user agent")
    with httpx.Client(timeout=20, headers={"User-Agent":f"NailMediaAI/0.1 ({contact})"}) as client:
        return CommonsCollector(client).search(keyword, limit)
