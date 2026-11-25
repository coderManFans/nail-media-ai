import httpx
import pytest
from nail_media.native_search import NativeBaiduSearch, parse_page

def test_parse():
    html='<img src="https://example.org/logo.png"><div class="imgitem"><img src="https://example.org/nail.jpg"></div>'
    assert len(parse_page(html,3))==1

def test_robots_denial():
    def handler(request):
        assert request.url.path=="/robots.txt"
        return httpx.Response(200,text="User-agent: *\nDisallow: /search/")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(PermissionError):
            NativeBaiduSearch(client).search("美甲",3)
