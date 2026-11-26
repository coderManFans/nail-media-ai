import imagehash
import numpy as np
from PIL import Image, ImageFilter, ImageStat, ImageOps

def features(path):
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        width,height = image.size
        image.thumbnail((256,256))
        hsv = np.asarray(image.convert("HSV"),dtype=np.int32)
        bins = (hsv[:,:,0]//32)*16 + (hsv[:,:,1]//64)*4 + hsv[:,:,2]//64
        hist = np.bincount(bins.ravel(),minlength=128).astype(float)
        hist /= hist.sum()
        sharpness = ImageStat.Stat(image.convert("L").filter(ImageFilter.FIND_EDGES)).stddev[0]
        return {"phash":str(imagehash.phash(image)), "dhash":str(imagehash.dhash(image)),
                "hist":hist.tolist(),"width":width,"height":height,"sharpness":sharpness}

def distance(a,b):
    return (int(a,16)^int(b,16)).bit_count()

def compare(a,b):
    p = distance(a["phash"],b["phash"])
    d = distance(a["dhash"],b["dhash"])
    color = sum(abs(x-y) for x,y in zip(a["hist"],b["hist"]))/2
    aspect = abs(a["width"]/a["height"] / (b["width"]/b["height"])-1)
    return {"phash_distance":p,"dhash_distance":d,"color_distance":color,
            "matched":p<=4 and d<=5 and color<=0.12 and aspect<=0.08}

def quality(f):
    return (min(f["width"],f["height"],1600),f["sharpness"])
