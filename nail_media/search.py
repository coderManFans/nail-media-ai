import argparse
from pathlib import Path
from .catalog import Catalog
from .commons import collect

def main():
    p = argparse.ArgumentParser()
    p.add_argument("keyword")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--contact", required=True)
    p.add_argument("--db", default="runtime/catalog.sqlite3")
    a = p.parse_args()
    items = collect(a.keyword, a.limit, a.contact)
    print(f"Found {len(items)} images; inserted {Catalog(Path(a.db)).add(items)} metadata records")

if __name__ == "__main__":
    main()
