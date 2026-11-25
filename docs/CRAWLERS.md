# Crawler integration
Scrapy is the generic crawler engine; robots.txt, single concurrent request, bounded retries, no redirects. Use only permitted pages.
Install Scrapy: pip install 'scrapy>=2.13,<3'
Run from root: python -m scrapy runspider nail_media/scrapy_spider.py -a url=https://example.org -a authorized=yes -O runtime/discovered.jsonl
Generate keyword task definitions: python -m nail_media.tasks
Keywords are planning records, not live scheduled jobs. Activate only after a permitted platform API or source is configured.
MediaCrawler (https://github.com/NanmiCoder/MediaCrawler) is research-only per upstream documentation; not bundled or executed. Baidu Images is not Baidu Tieba. Platform adapters remain pending.
