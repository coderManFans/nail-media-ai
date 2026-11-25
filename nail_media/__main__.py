import argparse
from pathlib import Path
from .catalog import Catalog
from .collectors import ManifestCollector, HtmlCollector

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db", default="runtime/catalog.sqlite3")
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("import")
    m.add_argument("file", type=Path)
    h = sub.add_parser("html")
    h.add_argument("file", type=Path)
    h.add_argument("--source", required=True)
    e = sub.add_parser("export")
    e.add_argument("file", type=Path)
    a = p.parse_args()
    c = Catalog(Path(a.db))
    if a.cmd == "export":
        print(c.export(a.file))
    else:
        payload = a.file.read_text(encoding="utf-8")
        items = ManifestCollector().collect(payload) if a.cmd == "import" else HtmlCollector().collect(payload, a.source)
        print(c.add(items))

if __name__ == "__main__":
    main()
