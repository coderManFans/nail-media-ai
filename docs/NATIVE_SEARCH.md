# Native Baidu search
Only enable when automated access is permitted by the site. The collector checks robots.txt and stops on denial, HTTP errors or redirects. No CAPTCHA solving or login bypass.
Install optional browser runtime: pip install playwright && python -m playwright install chromium
HTTP mode: BAIDU_NATIVE_MODE=http python -m nail_media.service --tasks config/baidu-smoke.json --once
Browser mode: BAIDU_NATIVE_MODE=browser python -m nail_media.service --tasks config/baidu-smoke.json --once
The .imgitem selector is provisional until verified against a live permitted page. Results are candidate metadata only, not download authorization. Browser mode is explicit, not an automatic fallback after denial.
