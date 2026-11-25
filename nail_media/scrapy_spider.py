import scrapy
from nail_media.collectors import HtmlCollector

class NailSpider(scrapy.Spider):
    name = "nail_authorized"
    custom_settings = {"ROBOTSTXT_OBEY": True, "CONCURRENT_REQUESTS": 1, "DOWNLOAD_DELAY": 3, "DOWNLOAD_TIMEOUT": 20, "RETRY_TIMES": 1, "RETRY_HTTP_CODES": [500, 502, 503, 504], "REDIRECT_ENABLED": False, "DOWNLOAD_MAXSIZE": 2000000}
    def __init__(self, url, authorized="no", **kwargs):
        super().__init__(**kwargs)
        if authorized != "yes" or not url.startswith("https://"):
            raise ValueError("Provide an authorized HTTPS page")
        self.start_urls = [url]
    def parse(self, response):
        for item in HtmlCollector().collect(response.text, response.url):
            yield item.record()
