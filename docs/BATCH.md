# V0.2.1 百度图片批量采集（本地）

## 更新和测试

```bash
cd ~/workspace/openWorkSpace/nail-media-ai
git pull
python -m pip install -e '.[test,crawler]'
python -m pytest tests/test_task_store.py tests/test_batch.py tests/test_icrawler_engine.py -v
```

## 生成受控的采集计划

以下命令仅生成 JSON，不会联网。首次建议只跑 2 个关键词，每词最多 3 张。

```bash
python -m nail_media.batch --platform baidu --category 款式 --limit 3 --max-tasks 2 --output runtime/baidu-batch.json
cat runtime/baidu-batch.json
```

使用一个新的运行目录，不影响已经验证的 `runtime/baidu-test`：

```bash
python -m nail_media.service --tasks runtime/baidu-batch.json --root runtime/baidu-batch --baidu-engine icrawler --once
python -m nail_media.service --tasks runtime/baidu-batch.json --root runtime/baidu-batch --status
```

**注意**：`--once` 表示扫描一次所有当前到期的任务，不意味着只运行一个关键词。运行目录必须与状态查询保持一致。

## 常驻任务调度

```bash
python -m nail_media.service --tasks runtime/baidu-batch.json --root runtime/baidu-batch --baidu-engine icrawler
```

此命令会一直运行，可按 Ctrl+C 停止。任务状态保存在 `tasks.sqlite3`，已经成功的任务到下一个采集周期才会再次被领取。失败任务按 60 秒、120 秒退避重试，最多尝试 3 次。无法配置或被禁止访问的任务不会自动重试。

崩溃留下的 `RUNNING` 任务默认要超过 3600 秒才能在下一次启动时恢复。若确认不存在其他采集进程，可以根据实际最长单次采集耗时设置 `--recover-after`，不得将其设成短于合法采集耗时的值。当前是单 worker 设计，**不要同时启动多个 service 进程操作同一个运行目录**。

## 查看本地资产

```bash
ls runtime/baidu-batch/images
sqlite3 runtime/baidu-batch/catalog.sqlite3 'SELECT COUNT(*) FROM crawler_assets;'
sqlite3 runtime/baidu-batch/catalog.sqlite3 'SELECT platform,keyword,COUNT(*) FROM crawler_observations GROUP BY platform,keyword;'
```

本版本 **不会自动推送 GitHub**。检查素材元数据及来源授权后，可用已有的归档命令操作：

```bash
python -m nail_media.archive --db runtime/baidu-batch/catalog.sqlite3 --checkout ../nail-media-data --confirm-authorized
```

归档为完整替换，**不可直接将另一个独立运行目录的导出结果覆盖已有三张图片的归档**。要保留全部资产，应优先复用同一个主素材数据库或先实现安全合并，再进行 GitHub 同步。

## 已知限制

- icrawler 适配器尚未存储原始媒体 URL，仅保存关键词、hash、尺寸及本地文件名
- pHash 阈值可能误判近似图；需人工审查误判案例
- 任务级失败恢复不等同于下载层逐张断点续传
- 单任务运行时间超出 lease 时，不应启动另一个服务实例
- 使用公开图片前仍需核查授权和来源
