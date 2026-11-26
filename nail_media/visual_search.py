"""Local normalized visual embeddings; model identity isolates indexes."""
import argparse
import json
import sqlite3
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from .video_assets import sha256_file

DEFAULT_MODEL="ViT-B-32"
DEFAULT_WEIGHTS="laion2b_s34b_b79k"

def translate_query(text):
    terms={"猫眼":"cat eye","法式":"French tips","渐变":"gradient","晕染":"marble","裸粉色":"nude pink","奶白色":"milky white","酒红色":"burgundy","奶茶色":"beige","碎钻":"rhinestones","珍珠":"pearls","杏仁甲":"almond nails","方圆甲":"squoval nails","短甲":"short nails","美甲":"nail art","粉色":"pink","红色":"red","蓝色":"blue","绿色":"green","黑色":"black","白色":"white","通勤":"office","婚礼":"wedding","简约":"minimalist"}
    for term in sorted(terms,key=len,reverse=True):
        text=text.replace(term," "+terms[term]+" ")
    return " ".join(text.split())

class Encoder:
    def __init__(self, model=DEFAULT_MODEL, weights=DEFAULT_WEIGHTS, device="auto"):
        import torch
        import open_clip
        self.torch=torch
        self.device=("mps" if torch.backends.mps.is_available() else "cpu") if device=="auto" else device
        self.identity=model+":"+weights+":v1"
        self.model,_,self.transform=open_clip.create_model_and_transforms(model,pretrained=weights,device=self.device)
        self.model.eval()
        self.tokenizer=open_clip.get_tokenizer(model)
    def image(self, image):
        with self.torch.inference_mode():
            return self.model.encode_image(self.transform(ImageOps.exif_transpose(image).convert("RGB")).unsqueeze(0).to(self.device)).float().cpu().numpy()[0]
    def text(self, text):
        with self.torch.inference_mode():
            return self.model.encode_text(self.tokenizer([translate_query(text)]).to(self.device)).float().cpu().numpy()[0]

def normalize(value):
    v=np.asarray(value,dtype="<f4")
    if v.ndim!=1 or not v.size or not np.isfinite(v).all():
        raise ValueError("Invalid vector")
    norm=np.linalg.norm(v)
    if not np.isfinite(norm) or norm<=0:
        raise ValueError("Invalid vector norm")
    return v/norm

def index(root, encoder, limit=20):
    if not 1<=limit<=1000:
        raise ValueError("Invalid limit")
    root=Path(root)
    if not (root/"catalog.sqlite3").is_file():
        raise FileNotFoundError(root)
    report={"indexed":0,"errors":[]}
    with sqlite3.connect(root/"catalog.sqlite3") as db:
        db.execute("CREATE TABLE IF NOT EXISTS image_vectors (image_sha TEXT, encoder TEXT, dimension INTEGER, vector BLOB, PRIMARY KEY(image_sha,encoder))")
        rows=db.execute("""SELECT a.sha256,a.payload FROM crawler_assets a
            JOIN image_clusters c ON c.representative_sha=a.sha256
            LEFT JOIN image_vectors v ON v.image_sha=a.sha256 AND v.encoder=?
            WHERE v.image_sha IS NULL ORDER BY a.sha256 LIMIT ?""",(encoder.identity,limit)).fetchall()
        for sha,raw in rows:
            try:
                path=root/"images"/Path(json.loads(raw)["path"]).name
                if path.is_symlink() or sha256_file(path)!=sha:
                    raise ValueError("Image integrity mismatch")
                with Image.open(path) as image:
                    v=normalize(encoder.image(image))
                with db:
                    db.execute("INSERT OR REPLACE INTO image_vectors VALUES (?,?,?,?)",(sha,encoder.identity,v.size,v.tobytes()))
                report["indexed"]+=1
            except Exception as exc:
                report["errors"].append({"image_sha":sha,"error":type(exc).__name__})
    return report

def search(root, encoder_id, query=None, *, limit=20, color=None, style=None, shape=None, eligible_only=True, tag_model="qwen2.5vl:7b"):
    if not 1<=limit<=100:
        raise ValueError("Invalid limit")
    q=normalize(query) if query is not None else None
    path=(Path(root)/"catalog.sqlite3").resolve()
    with sqlite3.connect(path.as_uri()+"?mode=ro",uri=True) as db:
        manual = dict(db.execute("SELECT image_sha,payload FROM manual_tags")) if db.execute("SELECT 1 FROM sqlite_master WHERE name='manual_tags' AND type='table'").fetchone() else {}
        rows=db.execute("""SELECT a.sha256,t.payload,v.dimension,v.vector
            FROM crawler_assets a JOIN image_clusters c ON c.representative_sha=a.sha256
            LEFT JOIN image_tags t ON t.image_sha=a.sha256 AND t.model=? AND t.version='v2'
            LEFT JOIN image_vectors v ON v.image_sha=a.sha256 AND v.encoder=?""",(tag_model,encoder_id))
        results=[]
        for sha,raw,dim,blob in rows:
            raw=manual.get(sha,raw)
            tags=json.loads(raw) if raw else {}
            if eligible_only and not tags.get("recommendation_eligible"):
                continue
            if color and color not in tags.get("colors",[]): continue
            if style and style not in tags.get("styles",[]): continue
            if shape and shape!=tags.get("nail_shape"): continue
            if q is not None:
                if dim!=q.size or blob is None: continue
                score=float(np.dot(q,np.frombuffer(blob,dtype="<f4")))
            else:
                score=float(tags.get("confidence",0))
            results.append({"image_sha":sha,"score":score,"tags":tags})
    return sorted(results,key=lambda r:(-r["score"],r["image_sha"]))[:limit]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default="runtime/media-library")
    p.add_argument("--limit",type=int,default=20)
    p.add_argument("--device",default="auto",choices=["auto","cpu","mps"])
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument("--index",action="store_true")
    group.add_argument("--image")
    group.add_argument("--text")
    p.add_argument("--color")
    p.add_argument("--style")
    p.add_argument("--shape")
    p.add_argument("--include-unreviewed",action="store_true")
    a=p.parse_args()
    encoder=Encoder(device=a.device)
    if a.index:
        result=index(a.root,encoder,a.limit)
    else:
        if a.image:
            with Image.open(a.image) as image:
                query=encoder.image(image)
        else:
            query=encoder.text(a.text)
        result=search(a.root,encoder.identity,query,limit=a.limit,color=a.color,style=a.style,shape=a.shape,eligible_only=not a.include_unreviewed)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
