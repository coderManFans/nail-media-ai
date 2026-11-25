from hashlib import sha256
from pathlib import Path
from PIL import Image
import imagehash

def inspect_image(path: Path, min_side=200, max_bytes=20_000_000):
    if path.stat().st_size > max_bytes:
        raise ValueError("Image too large")
    with Image.open(path) as img:
        if img.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValueError("Unsupported image format")
        w, h = img.size
        if min(w,h) < min_side or w*h > 25_000_000:
            raise ValueError("Image dimensions outside limits")
        img.verify()
    with Image.open(path) as img:
        fingerprint = str(imagehash.phash(img.convert("RGB")))
    return {"sha256":sha256(path.read_bytes()).hexdigest(),"phash":fingerprint,"width":w,"height":h}

def similar(a, b, threshold=6):
    return imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b) <= threshold
