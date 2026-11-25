import pytest
from nail_media.collectors import Media

def test_public_image_params():
    assert Media("https://image.baidu.com/","https://example.org/a.jpg?w=300&format=webp","baidu").record()

@pytest.mark.parametrize("suffix",["?token=secret","?w=300&sig=abc","?unknown=1","?w=https%3A%2F%2Fexample.org","#secret"])
def test_reject_unsafe_params(suffix):
    with pytest.raises(ValueError):
        Media("https://image.baidu.com/","https://example.org/a.jpg"+suffix,"baidu").record()
