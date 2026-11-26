import pytest
from nail_media.tiktok_video import validate_tiktok_url, normalize_info

URL = "https://www.tiktok.com/@_/video/7363977699095891205"

def test_tiktok_url():
    assert validate_tiktok_url(URL) == URL

@pytest.mark.parametrize("url",[
    "http://www.tiktok.com/@_/video/7363977699095891205",
    "https://evil.tiktok.com/@_/video/7363977699095891205",
    "https://www.tiktok.com/@_/video/7363977699095891205?token=abc",
    "https://www.tiktok.com/@_/video/not-a-number",
])
def test_reject_invalid(url):
    with pytest.raises(ValueError):
        validate_tiktok_url(url)

def test_metadata_normalization():
    result = normalize_info({"id":"7363977699095891205","title":"Simple Flower",
                             "duration":53,"uploader":"example"}, URL)
    assert result["record"]["platform"]=="tiktok"
    assert result["duration_seconds"]==53
    assert result["platform_id"]=="7363977699095891205"
