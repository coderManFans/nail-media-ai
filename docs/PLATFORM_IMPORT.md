# Platform export integration
This importer accepts authorized JSON arrays or JSONL files. It does not log in, search live platforms, or download media. Confirm source terms and rights before retaining metadata.
Baidu normalized export: source_url (Baidu result reference), image_url, title. Preserve original publisher URL in the upstream export; current catalog cannot retain it separately.
Xiaohongshu: note_url or source_url, image_list (array or comma-separated URLs), title/desc.
Douyin: aweme_url or source_url, title/desc. Video records are post references, not downloaded binaries.
Run: python -m nail_media.platform_import xiaohongshu runtime/imports/xhs.json --confirm-authorized
URLs containing query parameters or fragments are rejected by the existing catalog contract. Do not strip access tokens to bypass restrictions. Actual MediaCrawler export compatibility must be verified against an authorized sample and its license.
