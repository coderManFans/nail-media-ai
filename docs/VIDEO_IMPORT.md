# TikTok MP4 已通过的本地导入（无需再次下载）

用户已在 Mac 上成功运行 `yt-dlp` 下载 TikTok 公开美甲视频：
- 视频 ID：`7363977699095891205`
- 视频信息：标题包含 Simple Flower，时长 53 秒
- 本地文件：`runtime/tiktok-smoke/7363977699095891205.mp4`（约 1.90 MiB）
- JSON：`runtime/tiktok-smoke/7363977699095891205.info.json`

## 更新及验证

```bash
cd ~/workspace/openWorkSpace/nail-media-ai
git pull
python -m pytest tests/test_video_assets.py tests/test_tiktok_video.py -v
ffprobe -version
```

## 导入既有 MP4 到统一视频素材库

不需要再跑 `yt-dlp` 下载：

```bash
python -m nail_media.video_import \
  runtime/tiktok-smoke/7363977699095891205.mp4 \
  --source-url 'https://www.tiktok.com/@_/video/7363977699095891205' \
  --platform tiktok \
  --platform-id 7363977699095891205 \
  --title 'Simple Flower' \
  --root runtime/video-library
```

程序运行前通过 ffprobe 检查容器可解析、视频流存在、宽高时长有效，SHA256 计算内容哈希并将文件保存在 `runtime/video-library/videos/<sha256>.mp4`，注册媒体来源关系到 SQLite。重复执行不应复制第二份。

```bash
sqlite3 runtime/video-library/catalog.sqlite3 'SELECT COUNT(*) FROM video_assets;'
sqlite3 runtime/video-library/catalog.sqlite3 'SELECT COUNT(*) FROM video_sources;'
open runtime/video-library/videos
```

## 归档元数据

```bash
python -m nail_media.archive \
  --db runtime/video-library/catalog.sqlite3 \
  --checkout ../nail-media-data \
  --confirm-authorized
```

该命令仅写入本地数据仓库中的 `catalog/media.jsonl`，按 ID 合并之前图片及新增视频记录。人工审核内容并确认保留和发布权利后可自行 git add / commit / push。视频二进制文件不会上传 GitHub。

## 限制

- 此模块只导入已存在且获准保存的视频；尚未开发 TikTok 关键词发现
- `ffprobe` 必须可用；元数据用 ffprobe 获取而非仅相信文件后缀
- SHA256 用于完全相同的文件去重，后续再加入视频指纹去重和抽帧
- 平台来源 URL 通过主域名及 HTTPS 校验；不存储 Cookie、签名参数或授权令牌
- 小红书、抖音自动发现仍待独立验证
