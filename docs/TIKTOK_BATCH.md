# TikTok 批量入库（V0.5）

本功能使用已经人工确认、允许留存的 TikTok 视频 URL 清单，不提供自动联网关键词搜索、登录绕过或签名破解。

## 准备依赖

在 nail-media-ai 项目根目录执行：

```bash
python -m pip install -e '.[video,test]'
ffprobe -version
```

必须使用 Python 3.12+ 和可运行的 ffprobe（FFmpeg）。视频仅保存在本地素材库；GitHub 归档只保存脱敏元数据。

## 1. 创建可审核的发现清单

请使用自行核实的公开链接。以下地址是此前手动验证过的示例，请仅在具有保存权限时下载：

```bash
mkdir -p runtime
cat > runtime/tiktok-links.json <<'JSON'
[
  {
    "keyword": "nail art",
    "url": "https://www.tiktok.com/@_/video/7363977699095891205"
  }
]
JSON
```

如果需要经 DiscoveryProvider 检查 URL 并去重：

```bash
python -m nail_media.tiktok_discovery \
  --input runtime/tiktok-links.json \
  --keyword "nail art" \
  --limit 5 \
  --output runtime/tiktok-tasks.json
```

发现模块目前只接收本地 JSON 清单，不自动搜索 TikTok。输入中任意带 query/fragment/token 的视频 URL 都会被拒绝。输出文件提供标准化的 platform、platform_id、keyword、url 字段。

## 2. 导入已有的 TikTok 视频（推荐）

如果之前已经下载了示例 MP4，先把它导入抖音、小红书共用的素材库，无须重新访问 TikTok：

```bash
python -m nail_media.video_import \
  runtime/tiktok-smoke/7363977699095891205.mp4 \
  --source-url 'https://www.tiktok.com/@_/video/7363977699095891205' \
  --platform tiktok --platform-id 7363977699095891205 \
  --root runtime/media-library
```

如果本地没有上述文件，可跳过这一步；批量模块会按清单尝试下载。

**注意：** 早期独立测试素材库 `runtime/video-library` 不会自动并入 `runtime/media-library`。统一素材库请始终使用 `runtime/media-library`。

## 3. 批量处理

```bash
python -m nail_media.tiktok_batch \
  --input runtime/tiktok-tasks.json \
  --root runtime/media-library \
  --max-items 5 \
  --confirm-authorized
```

- 先校验 URL 和平台 ID；同一作品跨多个关键词只处理一次，关键词关联保存在 `video_keywords`。
- 下载前查询 `video_sources` 与 `video_assets`，校验本地文件 SHA256；已有完整素材则跳过网络请求。
- 单条任务异常会记录为 `failed`，其余任务继续执行。
- 已处理视频的任务状态和关键词持续保存在同一个 SQLite 数据库。
- 任务状态 `running` 默认在上次更新时间 3600 秒后允许恢复；应保证同一数据库只有一个批量任务进程。
- 失败任务不会在下次执行时自动重试；需要显式指定 `--retry-failed`。

## 4. 查询状态与重试

```bash
python -m nail_media.tiktok_batch --root runtime/media-library --status

python -m nail_media.tiktok_batch \
  --input runtime/tiktok-tasks.json \
  --root runtime/media-library \
  --retry-failed \
  --confirm-authorized
```

如果确定旧进程已经终止，可以通过 `--recover-after 60` 缩短中断恢复判断窗口；不要在其他采集进程仍在运行时使用。

批量报告：`runtime/media-library/reports/tiktok-batch.json`

下载中间文件：`runtime/media-library/tiktok-work/`

成功入库的视频：`runtime/media-library/videos/`

## 5. 归档 GitHub 数据仓库

先检查报告、来源和权限，确认可存储元数据后再执行已有的同步工具：

```bash
python -m nail_media.sync \
  --db runtime/media-library/catalog.sqlite3 \
  --checkout ../nail-media-data \
  --confirm-authorized-private
```

`Catalog.export` 会把每段视频的 `keywords` 关联信息包含在视频素材记录的 `sources` 中。不要将本地 MP4、下载缓存、访问令牌、Cookies 或会话信息提交到 GitHub。

## 边界

现阶段 TikTok 的关键词发现只支持审核过的离线清单；网络搜索适配器仍待验证。批量下载依赖公开作品当前可访问性、yt-dlp 支持情况及当地法律和平台规则。部分视频可能失败，属于正常的可观察状态，不会自动尝试绕过平台限制。
