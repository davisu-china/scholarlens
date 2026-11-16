# ScholarLens 本地接入指南

把 ScholarLens 从「fakes 端到端可跑」切换到「真实后端 + 真实模型」的完整步骤。

本指南分两条路线：
- **路线 A — 零依赖体验**：用内存 fakes，5 分钟跑起来，无需 Docker / GPU / 模型。先走这条确认代码没问题。
- **路线 B — 真实接入**：逐个接 Qdrant / Neo4j / Postgres / MinIO / LLM / 本地模型 / MinerU。

> 所有配置项都在 `core/config.py`，以环境变量前缀 `SL_` 覆盖（写进 `.env`）。
> 切换真假后端的总开关是环境变量 `SL_USE_REAL_ADAPTERS=1`（见 `apps/api/deps.py`）。

---

## 0. 前置条件

| 工具 | 版本 | 用途 |
|---|---|---|
| Python | 3.12+ | 后端 |
| [uv](https://docs.astral.sh/uv/) | 最新 | 依赖管理（`pip install uv` 或官方脚本） |
| Node.js | 18+ | 前端 |
| Docker + Docker Compose | 最新 | 基础设施（路线 B） |
| NVIDIA GPU + CUDA | 可选 | BGE / DeBERTa / MinerU 加速；CPU 也能跑但慢 |

---

## 路线 A：零依赖体验（fakes）

```bash
cd scholarlens

# 后端
uv sync --extra dev
uv run pytest -q                              # 应看到 55 passed
uv run uvicorn apps.api.main:app --reload     # http://localhost:8000

# 前端（另开终端）
cd apps/web
npm install
npm run dev                                   # http://localhost:3000
```

此时 `/query`、`/research` 已经能用——走的是内存 fakes，答案是 FakeLLM 的占位，但**整条链路（检索 → 生成 → 引用校验 → 前端角标）是真的**。确认界面能提问、能看到 Trace 和证据卡片后，再进路线 B。

快速用 curl 验证 SSE：

```bash
curl -N -X POST http://localhost:8000/query \
  -H 'Content-Type: application/json' \
  -d '{"question":"what is position interpolation"}'
```

---

## 路线 B-无GPU：全部用云 API（推荐，无需显卡）

本机不需要 GPU，只跑数据库 + API + 前端，AI 能力全部走云：

| 能力 | 云服务 | .env 配置 |
|---|---|---|
| LLM（生成/规划/判官） | airouter 等 OpenAI 兼容网关 | `SL_LLM_API_BASE` `SL_LLM_API_KEY` `SL_STRONG_MODEL=claude-opus-5-5` `SL_SMALL_MODEL=claude-haiku-5-5` |
| 向量化 + 重排 | 硅基流动 | `SL_SILICONFLOW_API_KEY`（bge-m3 / bge-reranker-v2-m3） |
| 引用校验 | LLM 判官 | `SL_NLI_MODE=llm`（默认，用小模型逐句判断，无需 DeBERTa） |
| PDF 解析 | MinerU 云 | `SL_MINERU_API_TOKEN` |

稀疏检索那一路（专有名词精确召回）用本地词法编码器补上，不需要模型。
配好 `.env` 后：

```bash
docker compose -f deploy/docker-compose.yml up -d   # 只需 Qdrant/Postgres/Neo4j/MinIO/Redis
export SL_USE_REAL_ADAPTERS=1
uv run uvicorn apps.api.main:app --reload
```

> 已用真实服务端到端验证：MinerU 解析一篇 18 页论文约 35s，硅基流动向量化入库，
> opus-5-5 生成答案、haiku 逐句校验引用。全程无需本地 GPU。

---

## 路线 B-GPU：本地跑模型

### B1. 启动基础设施

```bash
docker compose -f deploy/docker-compose.yml up -d
docker compose -f deploy/docker-compose.yml ps     # 五个服务都 Up
```

启动的服务与端口：

| 服务 | 端口 | 控制台 / 验证 |
|---|---|---|
| PostgreSQL 16 | 5432 | `psql postgresql://scholarlens:scholarlens@localhost:5432/scholarlens` |
| Qdrant | 6333 (HTTP) / 6334 (gRPC) | http://localhost:6333/dashboard |
| Neo4j 5 | 7687 (bolt) / 7474 (HTTP) | http://localhost:7474 （neo4j / scholarlens） |
| MinIO | 9000 (API) / 9001 (控制台) | http://localhost:9001 （minioadmin / minioadmin） |
| Redis 7 | 6379 | `redis-cli ping` → PONG |

### B2. 配置 `.env`

```bash
cp .env.example .env
```

关键项（其余保持默认即可对上 docker-compose）：

```ini
# 切换到真实 adapter（否则仍用 fakes）
SL_USE_REAL_ADAPTERS=1

# LLM：经 LiteLLM 路由。按你用的供应商填对应 key（见 B3）
SL_STRONG_MODEL=claude-sonnet-4-5      # Planner / Writer 用强模型
SL_SMALL_MODEL=qwen-plus               # Reflector / 改写用小模型
```

> `SL_USE_REAL_ADAPTERS` 不是 `core/config.py` 的字段，而是 `apps/api/deps.py` 直接读的环境变量。放进 `.env` 后需要用会加载 `.env` 的方式启动（或 `export`）。

### B3. 接入 LLM（LiteLLM）

adapter：`core/adapters/litellm_client.py`。[LiteLLM](https://docs.litellm.ai/) 用环境变量认证，模型名决定路由到哪家。

```bash
# 三选一或多选，取决于 SL_STRONG_MODEL / SL_SMALL_MODEL 指向谁
export ANTHROPIC_API_KEY=sk-ant-...        # claude-*
export DASHSCOPE_API_KEY=sk-...            # qwen-*（阿里云百炼）
export DEEPSEEK_API_KEY=sk-...             # deepseek-*
```

- 模型名写 LiteLLM 认识的形式（如 `claude-sonnet-4-5`、`qwen-plus`、`deepseek-chat`）。
- 本地 vLLM：把模型名设成 `openai/<model>` 并设 `OPENAI_API_BASE=http://localhost:8001/v1`。
- `structured()` 用 `response_format={"type":"json_object"}` 约束输出；若某供应商不支持，改用工具调用或在 prompt 里强约束（见 adapter 内注释）。

自测：

```bash
uv run python -c "
import asyncio
from core.adapters.litellm_client import LiteLLMClient
print(asyncio.run(LiteLLMClient().complete('说一句话确认你在工作')))
"
```

### B4. 下载并接入本地模型（BGE-M3 + reranker + DeBERTa-NLI）

adapter：`core/adapters/bge.py`、`core/adapters/nli.py`。模型用 `FlagEmbedding` 和 `transformers` 自动下载到 `~/.cache/huggingface`。

```bash
# 这些是重依赖，默认 pyproject 已声明；GPU 版 torch 需按官方指引单独装
uv run python -c "
from FlagEmbedding import BGEM3FlagModel
BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)      # 首次会下载 ~2GB
"
```

要点：
- **向量维度**：BGE-M3 dense 维度是 **1024**，与 `QdrantVectorStore(dense_dim=1024)` 默认一致。换别的 embedding 要同步改这个值，且**重建 Qdrant collection**。
- **国内下载慢**：设 `export HF_ENDPOINT=https://hf-mirror.com` 走镜像。
- **CPU 模式**：把 `use_fp16=False`，速度会明显下降，功能正常。
- **DeBERTa-NLI 标签顺序**：adapter 会从 `model.config.id2label` 里自动找 `entailment` 下标，换模型一般无需改代码；但若新模型标签命名不含 `entail` 字样，需要调整 `core/adapters/nli.py` 里的匹配逻辑。

### B5. 初始化 Qdrant / Postgres

Qdrant collection 在首次 `upsert` 时自动建（`ensure_collection`）。Postgres 表需要先建：

```bash
uv run python -c "
import asyncio
from core.adapters.postgres_tables import PostgresTableStore
asyncio.run(PostgresTableStore().init())          # 建 result_rows 表
"
```

Neo4j、MinIO 无需预建（MinIO 的 bucket 首次使用时自动创建）。

### B6-云. 用 MinerU 云 API 解析（推荐，无需 GPU）

adapter：`core/adapters/mineru_cloud.py`，已用真实论文验证（18 页约 30 秒）。

1. 在 https://mineru.net 的 API 管理页创建 token；
2. 写进 `.env`（该文件已被 gitignore，**不要**写进 `.env.example` 或代码）：
   ```ini
   SL_MINERU_API_TOKEN=你的token
   ```
3. 配好后 `/ingest/upload` 直接可用——即使其余组件还在用 fakes：
   ```bash
   curl -X POST http://localhost:8000/ingest/upload -F 'files=@paper.pdf'
   ```

说明：返回的坐标框已归一化到 0–1000、页码从 1 开始；参考文献由 MinerU 直接给出，
不需要 GROBID。限制：单文件 ≤200MB、≤200 页；每天 1000 页高优先级额度；论文内容会上传到
MinerU 服务器，未公开的论文请自行评估。没有 token 时才需要下面的本地 MinerU 方案。

### B6-本地. 接入 MinerU（PDF 解析）—— 最关键、最需要动手的一环

adapter：`core/adapters/mineru_parser.py`。这是整个系统**质量的上限**（PRD 第 07 章），也是唯一一个我留了 `NotImplementedError` 需要你按所用 MinerU 版本补全映射的地方。

步骤：

1. **按官方指引安装 MinerU（magic-pdf）**：https://github.com/opendatalab/MinerU 。它需要下载版面/公式/表格模型，GPU 强烈推荐。装完先用它自带的 CLI 确认能把一篇 PDF 解析出来。

2. **补全 `_run_mineru()`**：把 MinerU 的输出转成这个中间结构：
   ```python
   {
     "meta": {"title": str, "authors": [str], "year": int|None, "venue": str|None, "abstract": str},
     "blocks": [
       {
         "type": "text|equation|table|figure|caption",
         "content": "正文 / LaTeX公式 / HTML表格 / 图的VLM描述",
         "bboxes": [{"page": int, "x0": f, "y0": f, "x1": f, "y1": f}],
         "section_path": ["3 Method", "3.2 ..."],   # 可选
         "caption": "表/图标题"                        # 可选
       }, ...
     ]
   }
   ```
   `_to_block()` 已经把这个结构映射到 `PaperIR.Block`，所以你只要让 `_run_mineru` 吐出上面的字典即可。MinerU 不同版本的字段名不一样（`magic_pdf` 的 `pipe_mk_uni_format()` 产物），以你装的版本为准——这就是我不能在无 GPU 沙箱里替你定死的原因。

3. **坐标系对齐**：`bbox` 必须是 PDF 原始坐标（左下原点或左上原点要和前端 `react-pdf` 的高亮层约定一致），否则引用高亮会错位。建议先解析一篇、在前端点一次角标验证高亮位置。

4. **参考文献（可选）**：`_parse_references()` 接 [GROBID](https://github.com/kermitt2/grobid)。起一个 GROBID 服务（`docker run -p 8070:8070 lfoppiano/grobid:0.8.0`），把 `grobid_url` 传进 `MinerUParser(grobid_url="http://localhost:8070")`，解析 `/api/processReferences` 的 TEI XML 为 `Reference`。引用图谱（F6）依赖这步；不接则引用图为空，不影响问答。

### B7. 跑离线导入（Celery worker）

```bash
# 启动 worker
uv run celery -A apps.worker.celery_app worker -l info

# 上传一篇 PDF 走同步 API（会调用 parser + indexer）
curl -X POST http://localhost:8000/ingest/upload \
  -F 'files=@/path/to/paper.pdf'
```

或在代码里直接投递异步任务：

```python
from apps.worker.celery_app import ingest_paper
ingest_paper.delay("minio-key-of-uploaded.pdf")
```

导入成功后，Qdrant dashboard 里能看到 `scholarlens` collection 有了向量，就可以在前端提问了。

### B8. 启动完整应用

```bash
# 终端 1：API（真实后端）
SL_USE_REAL_ADAPTERS=1 uv run uvicorn apps.api.main:app --reload

# 终端 2：worker
uv run celery -A apps.worker.celery_app worker -l info

# 终端 3：前端
cd apps/web && npm run dev
```

---

## 可观测性（可选，PRD 非功能需求）

- **Langfuse**（LLM 调用 trace / 成本）：自托管后在 `.env` 填 `SL_LANGFUSE_HOST/PUBLIC_KEY/SECRET_KEY`，并在 LiteLLM adapter 里挂 Langfuse callback。
- **Prometheus + Grafana**：`prometheus-client` 已在依赖里，给 FastAPI 挂 `/metrics` 后用 Grafana 看面板。

---

## 跑评测

```bash
# 准备一个 JSONL：每行 {"qid","question","gold_answer","gold_evidence_ids","answerable"}
uv run python -m eval.cli path/to/dev.jsonl
```

消融矩阵（B0→+6）定义在 `eval/ablation.py`，`run_ablation` 对每个配置装不同 adapter 组合后评测。真实数值填进 PRD 第 12 章的表格。

---

## 排错速查

| 症状 | 原因 / 处理 |
|---|---|
| 启动仍走 fakes | `SL_USE_REAL_ADAPTERS` 没被进程读到；用 `export` 或确认启动方式加载了 `.env` |
| Qdrant 维度报错 | embedding 维度 ≠ collection 维度；改 `dense_dim` 并删掉旧 collection 重建 |
| 模型下载慢/失败 | `export HF_ENDPOINT=https://hf-mirror.com`；或预先手动下载到 HF 缓存 |
| NLI 概率恒为 0/异常 | 换的 NLI 模型标签命名不含 `entail`；改 `core/adapters/nli.py` 的标签匹配 |
| 引用高亮位置错 | MinerU bbox 坐标系与前端不一致；统一原点与缩放 |
| LLM `structured` 解析失败 | 供应商不支持 `json_object`；改用工具调用或强约束 prompt |
| `psycopg` 安装失败 | 需要本机 libpq；或用 `psycopg[binary]`（已在依赖里） |
| worker 任务一直 retry | parser 的 `_run_mineru` 还是 `NotImplementedError`；先完成 B6 |

---

## 一句话总结接入顺序

基础设施(B1) → `.env`(B2) → LLM(B3) → 本地模型(B4) → 建表/collection(B5) → **MinerU(B6，最花时间)** → 导入一篇(B7) → 起全套(B8)。先用一篇 PDF 打通端到端，再批量导入。
