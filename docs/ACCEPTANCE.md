# V1.1.0 本地统一验收

## macOS 原生启动（推荐，支持 MPS）

在仓库根目录执行：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[api,vision,test]'
python -m pytest -q
NAIL_MEDIA_ENABLE_WRITES=1 uvicorn nail_media.api:app --host 127.0.0.1 --port 8000
```

另一个终端：

```bash
cd frontend
npm install
npm run build
npm run dev
```

打开 http://127.0.0.1:5173 。API 文档 http://127.0.0.1:8000/docs 。

## Docker 只读浏览与检索

```bash
docker compose up --build
```

复用 runtime 目录和独立 Hugging Face 缓存。容器使用 CPU，不支持 macOS MPS；首次可能重新下载权重。默认关闭写入，采集与 Ollama 标签生产建议在宿主机运行。不要同时运行两个写入同一素材库的任务。

## 验收清单

| 场景 | 操作 | 预期 |
|---|---|---|
| 启动 | pytest、npm build、启动服务 | 无构建错误 |
| 素材 | 浏览分页、打开图片 | 图片和标签正常 |
| 检索 | 英文、中文领域词、上传图片 | 返回相似素材 |
| 人工审核 | 修改已有完整标签 JSON | 原 AI 标签保留，检索使用人工标签 |
| 后台任务 | 启动 index，刷新日志 | 增量向量生成 |
| 流水线 | production_pipeline --once | 完成或带警告完成 |
| 推荐 | 运行 recommendation | 人工标签优先 |
| 归档 | 导出 JSONL | 包含 manual_tag 等记录 |
| 恢复 | 中断后 --resume | 跳过成功阶段 |
| Docker | compose up | 本地只读界面可用 |

生产流水线默认不采集、不推送远程。配置 vector_limit 可启用增量向量生成。外部采集和私有归档需明确授权。中文词汇映射不是完整翻译，检索准确率需要人工评估。
