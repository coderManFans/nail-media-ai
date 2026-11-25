import io
import httpx
import pytest
from PIL import Image
from nail_media.download import download_image

def test_download(tmp_path):
    b = io.BytesIO()
    Image.new("RGB",(300,300),"red").save(b,format="PNG")
    def handler(request):
        return httpx.Response(200,headers={"content-type":"image/png"},content=b.getvalue())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        url = "https://upload.wikimedia.org/example.png"
        with pytest.raises(PermissionError):
            download_image(client,url,tmp_path)
        a = download_image(client,url,tmp_path,authorized=True)
        assert a == download_image(client,url,tmp_path,authorized=True)
        assert len(list(tmp_path.iterdir())) == 1
        with pytest.raises(ValueError):
            download_image(client,url,tmp_path,authorized=True,max_bytes=1)
        assert len(list(tmp_path.iterdir())) == 1
