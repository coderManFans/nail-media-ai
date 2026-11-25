"""Normalize explicitly mapped image fields from authorized JSON responses."""
from .collectors import Media

def extract_json_images(rows,source_url,platform,image_field="url",limit=20):
    if not 1<=limit<=20:
        raise ValueError("Invalid limit")
    items=[]
    seen=set()
    for row in rows:
        if not isinstance(row,dict):
            continue
        url=row.get(image_field)
        if not isinstance(url,str) or url in seen:
            continue
        item=Media(source_url,url,platform,title=str(row.get("title") or ""))
        try:
            item.record()
        except ValueError:
            continue
        seen.add(url)
        items.append(item)
        if len(items)==limit:
            break
    return items
