# Video frames

Install FFmpeg and verify ffmpeg -version. From the project root:

```bash
python -m nail_media.video_frames --root runtime/media-library --interval 2 --maximum 30 --limit 20
```

The interval is in seconds. Maximum bounds candidate frames per video (not guaranteed retained frames). Limit bounds attempted videos per invocation. Identical successful extraction settings are skipped. Images are saved in images/ and linked via video_frames. Quality thresholds are heuristic brightness, contrast and edge strength checks; frame times are estimates, not original presentation timestamps. pHash filtering is within one video run only. Scene detection and archive export of frame provenance are not implemented yet. Run one worker at a time.

```bash
sqlite3 runtime/media-library/catalog.sqlite3 'SELECT COUNT(*) FROM video_frames;'
python -m pytest tests/test_video_frames.py -v
```
