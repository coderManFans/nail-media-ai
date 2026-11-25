from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit
from .image_processing import inspect_image

def download_image(client, url, root, *, authorized=False, max_bytes=20_000_000, allowed_hosts=("upload.wikimedia.org",)):
    if not authorized:
        raise PermissionError("Explicit download permission required")
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in allowed_hosts or p.username or p.password or p.port not in (None,443) or p.query or p.fragment:
        raise ValueError("Only approved direct HTTPS media hosts are supported")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with NamedTemporaryFile(dir=root, delete=False) as f:
            temp = Path(f.name)
            with client.stream("GET", url, follow_redirects=False) as response:
                response.raise_for_status()
                if response.headers.get("content-type","").split(";")[0] not in {"image/jpeg","image/png","image/webp"}:
                    raise ValueError("Unsupported content type")
                size = 0
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > max_bytes:
                        raise ValueError("Download exceeds limit")
                    f.write(chunk)
        result = inspect_image(temp, max_bytes=max_bytes)
        target = root / result["sha256"]
        if not target.exists():
            temp.replace(target)
        return {**result,"path":str(target)}
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
