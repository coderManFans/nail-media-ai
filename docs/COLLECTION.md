# Unified collection

Run existing offline tasks:
```bash
python -m nail_media.orchestrator --once --confirm-authorized
```

Optional hourly metadata synchronization:
```bash
python -m nail_media.orchestrator --confirm-authorized --sync-checkout ../nail-media-data --confirm-authorized-private
```

For authorized MediaCrawler detail collection, add a task to a local copy of config/collection.json (keep it in config/ so relative paths work):
```json
{"id":"dy-detail-local","platform":"douyin","mode":"detail","project":"../../MediaCrawler","specified_ids":["YOUR_AUTHORIZED_VIDEO_ID"],"limit":1,"interval_hours":24,"enabled":true}
```

Use --config config/collection.local.json. Keep local identifiers and access tokens out of Git. Use the existing MediaCrawler browser login; interactive QR login may be required. The adapter runs detail mode only because the upstream search limit was not reliable in local testing. No automatic keyword search is implemented by this adapter. Run one worker per catalog. Failed subprocess output directories are temporary and removed; retry collection if needed. Sync runs after a cycle, not concurrently, with a 120-second retry delay on failure. Use --once for a single cycle.
