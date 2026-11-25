import httpx
from nail_media.providers import ConfiguredSearch

def test_gateway():
    def handler(request):
        assert request.url.params["keyword"] == "猫眼美甲"
        return httpx.Response(200,json={"items":[{"source_url":"https://www.xiaohongshu.com/explore/example","media_type":"post"},{"source_url":"https://example.org/post"}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = ConfiguredSearch(client,"https://example.org/search","xiaohongshu").search("猫眼美甲",20)
        assert len(result) == 1
        assert result[0].platform == "xiaohongshu"
