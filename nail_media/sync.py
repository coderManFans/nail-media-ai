import argparse
import subprocess
from pathlib import Path
from .archive import stage_catalog

def sync(db, checkout, *, confirmed=False):
    if not confirmed:
        raise PermissionError("Confirm metadata publication rights and private repository")
    root = Path(checkout).resolve()
    def git(*args):
        return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()
    if git("remote","get-url","origin") not in {
        "https://github.com/coderManFans/nail-media-data.git",
        "https://github.com/coderManFans/nail-media-data",
        "git@github.com:coderManFans/nail-media-data.git",
    }:
        raise ValueError("Unexpected archive repository")
    if git("branch","--show-current") != "main":
        raise ValueError("Archive checkout must be on main")
    if git("status","--porcelain"):
        raise ValueError("Archive checkout must be clean")
    git("pull","--ff-only","origin","main")
    count = stage_catalog(db,root)
    git("add","--","catalog/media.jsonl")
    if git("diff","--cached","--name-only"):
        git("commit","-m","Update authorized media catalog","--","catalog/media.jsonl")
    git("push","origin","HEAD:main")
    return count

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db",default="runtime/catalog.sqlite3")
    p.add_argument("--checkout",required=True)
    p.add_argument("--confirm-authorized-private",action="store_true")
    a = p.parse_args()
    print(sync(a.db,a.checkout,confirmed=a.confirm_authorized_private))

if __name__ == "__main__":
    main()
