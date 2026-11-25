"""Render a permitted public page with an ordinary Chromium session."""
def render(url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        try:
            page=browser.new_page(user_agent="NailMediaAI/0.1")
            response=page.goto(url,wait_until="domcontentloaded",timeout=30000)
            if response is None or response.status>=400:
                raise RuntimeError("Browser navigation failed")
            if page.url.split("?")[0]!=url.split("?")[0]:
                raise PermissionError("Unexpected navigation")
            try:
                page.locator(".imgitem img").first.wait_for(timeout=8000)
            except Exception:
                pass
            return page.content()
        finally:
            browser.close()
