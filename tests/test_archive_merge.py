from nail_media.archive import merge_records


def asset(sha, word):
    return {
        "id": sha,
        "record_type": "image_asset",
        "sha256": sha,
        "filename": sha + ".jpg",
        "observations": [
            {"platform":"baidu", "keyword":word, "observed_sha":sha, "match_type":"original"}
        ],
    }


def test_merge_preserves_existing_assets():
    result = merge_records([asset("old", "猫眼美甲")], [asset("new", "法式美甲")])
    assert [r["id"] for r in result] == ["new", "old"]


def test_merge_observations_and_idempotence():
    records = merge_records([asset("same", "猫眼美甲")], [asset("same", "法式美甲")])
    assert len(records) == 1
    assert {r["keyword"] for r in records[0]["observations"]} == {"猫眼美甲", "法式美甲"}
    assert merge_records(records, records) == records
