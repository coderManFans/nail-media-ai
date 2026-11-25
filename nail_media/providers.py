import httpx
from .commons import CommonsCollector
from .collectors import Media, platform_for

class ConfiguredSearch:
    """Adapter for an operator-authorized search gateway returning normalized items."""
    def __init__(self, client, endpoint, platform, token=None):
        if not endpoint.startswith("https://"):
            raise ValueError("HTTPS gateway required")
        self.client, self.endpoint, self.platform = client, endpoint, platform
        self.headers = {"Authorization": "Bearer " + token} if token else {}
    def search(self, keyword, limit):
        response = self.client.get(self.endpoint, params={"keyword":keyword,"limit":limit}, headers=self.headers, follow_redirects=False)
        response.raise_for_status()
        items = []
        for row in response.json()["items"][:limit]:
            if platform_for(row["source_url"]) != self.platform:
                continue
            item = Media(row["source_url"],row.get("media_url",row["source_url"]),self.platform,row.get("media_type","post"),row.get("title",""))
            item.record()
            items.append(item)
        return items
