"""Run an explicitly configured MediaCrawler detail job in its own uv environment."""
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from .mediacrawler_import import import_batch


def collect(task, root, *, runner=subprocess.run, importer=import_batch):
    project = Path(task["project"]).resolve()
    if not (project / "main.py").is_file():
        return {"status":"unconfigured","errors":["missing_mediacrawler"]}
    platform = task["platform"]
    ids = task["specified_ids"]
    if not isinstance(ids,list) or not 1 <= len(ids) <= task["limit"]:
        raise ValueError("Invalid detail list")
    if any(not isinstance(x,str) or not x.strip() or "," in x for x in ids):
        raise ValueError("Invalid detail identifier")
    env = os.environ.copy()
    env.pop("VIRTUAL_ENV",None)
    root = Path(root).resolve()
    root.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix="mc-",dir=root) as directory:
        command = ["uv","run","main.py","--platform",
                   {"xiaohongshu":"xhs","douyin":"dy"}[platform],
                   "--lt","qrcode","--type","detail","--specified_id",",".join(ids),
                   "--crawler_max_notes_count",str(task["limit"]),
                   "--max_concurrency_num","1","--get_comment","false",
                   "--get_sub_comment","false","--get_media","true",
                   "--save_data_option","jsonl","--save_data_path",directory,
                   "--headless","false"]
        result = runner(command,cwd=project,env=env,timeout=900,check=False)
        if result.returncode:
            return {"status":"failed","errors":["mediacrawler_exit"]}
        report = importer(directory,root,task["limit"],platform)
        return {**report,"status":"partial" if report["errors"] else
                ("success" if report["posts"] else "empty_or_filtered")}
