import json
import sqlite3
from PIL import Image, ImageDraw
from nail_media.video_frames import process
from nail_media.video_assets import sha256_file
from nail_media.catalog import Catalog


def test_frames_filter_and_resume(tmp_path):
    root = tmp_path
    Catalog(root / "catalog.sqlite3")
    (root / "videos").mkdir()
    video = root / "videos" / "sample.mp4"
    video.write_bytes(b"fake video")
    sha = sha256_file(video)
    with sqlite3.connect(root / "catalog.sqlite3") as db:
        db.execute("CREATE TABLE video_assets (sha256 TEXT PRIMARY KEY,payload TEXT)")
        db.execute("INSERT INTO video_assets VALUES (?,?)",(sha,json.dumps({"filename":video.name})))
    def extractor(video,directory,interval,maximum):
        image = Image.new("RGB",(320,320),"white")
        draw = ImageDraw.Draw(image)
        for x in range(0,320,20):
            for y in range(0,320,20):
                if (x//20+y//20)%2:
                    draw.rectangle((x,y,x+19,y+19),fill="black")
        paths = [directory / f"{i}.jpg" for i in range(3)]
        image.save(paths[0])
        image.save(paths[1])
        Image.new("RGB",(320,320),"black").save(paths[2])
        return paths
    first = process(root,extractor=extractor)
    assert first["frames"] == 1
    assert first["duplicates"] == 1
    assert first["filtered"] == 1
    assert not first["errors"]
    second = process(root,extractor=extractor)
    assert second["skipped"] == 1 and second["frames"] == 0
    with sqlite3.connect(root / "catalog.sqlite3") as db:
        assert db.execute("SELECT COUNT(*) FROM video_frames").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM crawler_assets").fetchone()[0] == 1
