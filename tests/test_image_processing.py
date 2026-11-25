from PIL import Image
from nail_media.image_processing import inspect_image, similar

def test_image(tmp_path):
    p = tmp_path / "a.png"
    Image.new("RGB",(300,300),"red").save(p)
    result = inspect_image(p)
    assert result["width"] == 300
    assert len(result["sha256"]) == 64
    assert similar(result["phash"],result["phash"])
