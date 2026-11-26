# TikTok 视频接入 V0.3（独立验证入口）

已在 Mac 上人工验证以下公开视频可以被 yt-dlp **解析**：视频 ID 7363977699095891205，标题包含 Simple Flower，时长 53 秒。尚待验证本机实际文件下载。

## 安装

```bash
cd ~/workspace/openWorkSpace/nail-media-ai
git pull
python -m pip install -e '.[test,video]'
python -m pytest tests/test_tiktok_video.py -v
```

## 先解析，不下载

```bash
python -m nail_media.tiktok_video \
  'https://www.tiktok.com/@_/video/7363977699095891205'
```

## 下载有权保留的公开视频

```bash
python -m nail_media.tiktok_video \
  'https://www.tiktok.com/@_/video/7363977699095891205' \
  --download \
  --root runtime/tiktok-smoke \
  --db runtime/tiktok-smoke/catalog.sqlite3
```

成功后在 `runtime/tiktok-smoke` 查看原始视频及对应的 `.info.json`，SQLite 的 `media` 表中保存作品级来源链接元数据。输出不会自动推送 GitHub。

若出现 impersonation 警告但解析正常，则无需处理；若出现访问错误，可按 yt-dlp 官方说明安装可选依赖，或检查网络/作品可用性。解析成功并不能保证实际下载成功。

当前工具实现的是 **已知公开链接的作品解析/下载**，尚未提供 TikTok 关键词搜索和自动发现，因此不会替代抖音及小红书的关键词采集适配器。

只下载你有权保存和使用的公开作品；不尝试绕过登录、验证码、签名或访问限制。
