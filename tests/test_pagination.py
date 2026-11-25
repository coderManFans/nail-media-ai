from nail_media.pagination import collect_pages
from nail_media.json_images import extract_json_images

def test_pages():
    calls=[]
    def fetch(page):
        calls.append(page)
        return extract_json_images([{"url":"https://example.org/a.jpg"},{"url":f"https://example.org/{page}.jpg"}],"https://example.org/gallery","generic")
    assert len(collect_pages(fetch,limit=3))==3
    assert calls==[1,2]

def test_json_rejects_invalid():
    assert len(extract_json_images([{"url":"http://example.org/a.jpg"},{"url":"https://example.org/b.jpg"}],"https://example.org/gallery","generic"))==1
