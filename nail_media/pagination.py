"""Bounded pagination for authorized search providers."""
def collect_pages(fetch_page,limit=20,max_pages=3):
    if not 1<=limit<=20 or not 1<=max_pages<=3:
        raise ValueError("Invalid collection bounds")
    seen=set()
    items=[]
    for page in range(1,max_pages+1):
        batch=fetch_page(page)
        if not batch:
            break
        added=0
        for item in batch:
            key=item.record()["id"]
            if key in seen:
                continue
            seen.add(key)
            items.append(item)
            added+=1
            if len(items)==limit:
                return items
        if not added:
            break
    return items
