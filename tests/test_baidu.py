import httpx
import pytest
from nail_media.baidu import ApiHzSearch, FallbackSearch
def test_search():
    def handler(request):
        assert request.method == "POST"
        assert b"words=" in request.content
        return httpx.Response(200,json={"code":200,"res":["https://example.org/a.jpg","https://example.org/b.jpg?token=x"]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert len(ApiHzSearch(client,"id","key").search("猫眼美甲",3)) == 1

def test_fallback():
    class Provider:
        def __init__(self, result): self.result = result
        def search(self,*args): return self.result
    assert FallbackSearch(Provider([]),Provider([1])).search("nail",1)==[1]
    assert FallbackSearch(Provider([2]),Provider([1])).search("nail",1)==[2]
