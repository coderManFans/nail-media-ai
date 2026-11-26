from nail_media.visual_search import translate_query

def test_domain_translation():
    assert translate_query("裸粉色猫眼美甲")=="nude pink cat eye nail art"
    assert translate_query("pink nails")=="pink nails"
