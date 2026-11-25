from nail_media.image_crawler import RateLimiter, extract_images

def test_extract():
    html='<img src="/a.jpg"><img src="/a.jpg"><img data-src="//example.org/b.png"><img src="data:image/png;base64,abc">'
    items=extract_images(html,"https://example.org/gallery","generic")
    assert [i.media_url for i in items]==["https://example.org/a.jpg","https://example.org/b.png"]

def test_rate_limit():
    now=[0]
    sleeps=[]
    def sleep(seconds):
        sleeps.append(seconds)
        now[0]+=seconds
    limiter=RateLimiter(clock=lambda:now[0],sleep=sleep)
    limiter.wait("https://example.org/a")
    limiter.wait("https://example.org/b")
    limiter.wait("https://example.net/a")
    assert sleeps==[5]
