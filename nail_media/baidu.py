"""Documented third-party Baidu-source search API."""
from urllib.parse import urlsplit
import json
from .collectors import Media

class ApiHzSearch:
    endpoint = "https://cn.apihz.cn/api/img/apihzimgbaidu.php"
    def __init__(self, client, user_id, key):
        self.client, self.user_id, self.key = client,user_id,key
    def search(self, keyword, limit):
        if not 1 <= limit <= 100 or not 1 <= len(keyword) <= 10:
            raise ValueError("Keyword or limit outside API bounds")
        try:
            response = self.client.post(self.endpoint,data={"id":self.user_id,"key":self.key,"words":keyword,"limit":limit,"page":1,"type":1},follow_redirects=False)
            print('Baidu HTTP status:', response.status_code, flush=True)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            print('Baidu request exception:', type(exc).__name__, flush=True)
            raise RuntimeError("Baidu search transport or response failure") from None
        code = str(data.get("code"))
        print("Baidu response diagnostics:", json.dumps({"code":code if code.isdigit() and len(code)<=8 else "unknown","res_type":type(data.get("res")).__name__}),flush=True)
        if str(data.get("code")) != "200" or not isinstance(data.get("res"),list):
            message = str(data.get("msg") or data.get("message") or "").lower()
            categories = {"rate_limit": ("频率","频次","限流","rate limit","次数"), "credentials": ("密钥","账号","认证","credential","key"), "parameter": ("参数","parameter"), "quota": ("余额","额度","quota"), "upstream": ("上游","维护","upstream")}
            print("Baidu rejection category:", next((name for name,terms in categories.items() if any(term in message for term in terms)), "unknown"), flush=True)
            raise RuntimeError("Baidu search API rejected request")
        items = []
        stats = {"raw_count":len(data["res"]),"non_string":0,"invalid_url":0,"query_or_fragment":0,"non_https":0,"object_keys":[]}
        for url in data["res"][:limit]:
            if isinstance(url,dict):
                stats["object_keys"] = sorted(set(stats["object_keys"]) | {k for k in url if k in {"url","image_url","imageUrl","thumbURL","objURL","middleURL","src","pic","title"}})
                url = next((url[k] for k in ("image_url","imageUrl","url","objURL","middleURL","thumbURL","src","pic") if isinstance(url.get(k),str)),None)
            if not isinstance(url,str):
                stats["non_string"] += 1
                continue
            item = Media("https://image.baidu.com/",url,"baidu",title="")
            try:
                item.record()
            except ValueError:
                stats["invalid_url"] += 1
                try:
                    parsed = urlsplit(url)
                    stats["query_or_fragment"] += int(bool(parsed.query or parsed.fragment))
                    stats["non_https"] += int(parsed.scheme != "https")
                except ValueError:
                    pass
                continue
            items.append(item)
        print("Baidu search diagnostics: " + json.dumps({**stats,"accepted":len(items)}),flush=True)
        return items

class FallbackSearch:
    def __init__(self, primary, secondary):
        self.primary,self.secondary = primary,secondary
    def search(self, keyword, limit):
        # Do not retry authentication errors, rate limits or access denials.
        # Fall back only on a successful empty result.
        items = self.primary.search(keyword,limit)
        return items if items else self.secondary.search(keyword,limit)
