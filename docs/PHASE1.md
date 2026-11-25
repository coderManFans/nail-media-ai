# Phase 1
Current: local authorized HTML and JSON manifest import, platform classification, URL deduplication, SQLite, JSONL export.
Next: permitted network discovery adapters, media download with explicit rights, content hashing, task scheduling, API and UI.
GitHub archive: export locally, inspect metadata, then commit to a separate private repository. No automatic upload while the data repository is public.
No real platform API or live collection is implemented yet. No LLM required.
Run:
    python -m pip install -e '.[test]'
    python -m nail_media import examples/manifest.json
    python -m nail_media export runtime/catalog.jsonl
    python -m pytest
