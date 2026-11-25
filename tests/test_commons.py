import httpx
from nail_media.commons import CommonsCollector

def test_search():
    def handler(request):
        assert request.url.params["gsrsearch"] == "nail art"
        return httpx.Response(200,json={"query":{"pages":[{"title":"File:Example.jpg","imageinfo":[{"mime":"image/jpeg","descriptionurl":"https://commons.wikimedia.org/wiki/File:Example.jpg","url":"https://upload.wikimedia.org/example.jpg"}]}]}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        items = CommonsCollector(client).search("nail art")
        assert len(items) == 1
        assert items[0].license_status == "unknown"
