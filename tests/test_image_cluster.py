from PIL import Image, ImageDraw
from nail_media.image_features import features, compare
from nail_media.cluster_pipeline import cluster
from nail_media.similarity_index import BKTree

def test_color_guard_and_resize(tmp_path):
    items = {}
    for name,color,size in [("red","red",400),("red_small","red",300),("blue","blue",400)]:
        image = Image.new("RGB",(size,size),color)
        ImageDraw.Draw(image).rectangle((size//4,size//4,size//2,size//2),fill="white")
        path = tmp_path/(name+".png")
        image.save(path)
        items[name] = features(path)
    assert compare(items["red"],items["red_small"])["matched"]
    assert not compare(items["red"],items["blue"])["matched"]
    groups = cluster(items)
    assert len(groups)==2
    assert {sha for sha,_ in groups["red"]}=={"red","red_small"}

def test_bk_tree():
    tree = BKTree()
    for key in ("00","01","ff","03"):
        tree.add(key,key)
    assert set(tree.search("00",1))=={"00","01"}
