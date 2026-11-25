from nail_media.platform_import import normalize

def test_baidu():
    items,rejected = normalize("baidu",[{"source_url":"https://image.baidu.com/example","image_url":"https://example.org/a.jpg"}])
    assert len(items)==1 and rejected==0

def test_xhs():
    items,rejected = normalize("xiaohongshu",[{"note_url":"https://www.xiaohongshu.com/explore/example","image_list":"https://example.org/a.jpg,https://example.org/b.jpg?token=secret"}])
    assert len(items)==1 and rejected==1

def test_douyin():
    items,rejected = normalize("douyin",[{"aweme_url":"https://www.douyin.com/video/123","desc":"example"},{"aweme_url":"https://example.org/video/123"}])
    assert len(items)==1 and rejected==1
    assert items[0].media_type=="video"
