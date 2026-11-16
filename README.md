# ScholarLens · 可溯源的学术深度研究引擎

解析论文 PDF、在私有文献库上做混合检索与多跳研究，生成**带引用的研究综述**——
每一句结论都能回溯到原文的页码与坐标，并经过逐句引用校验。

- **可溯源**：答案里每个论断都带 `[eid]` 角标，精确到原文位置
- **反幻觉**：生成后用 NLI/LLM 逐句校验引用是否成立，不达标的句子重写或标红
- **深度研究**：Agent 按「证据覆盖度」决定何时停止补检索，输出结构化综述
- **多模型**：Claude / DeepSeek 等按需切换，支持套餐、配额与用量计量
- **无需 GPU**：解析、向量化、重排、校验全部可走云 API

---

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.12 · FastAPI · Celery |
| 前端 | Next.js 14 · TypeScript · Tailwind · shadcn/ui |
| 检索 | BGE-M3（dense+sparse）· bge-reranker-v2-m3 · RRF 融合 |
| Agent | 自研协调器（Plan→Research→Reflect→Write→Verify）|
| 解析 | MinerU（版面 / 公式 / 表格 / 坐标）|
| LLM 网关 | LiteLLM（Claude via airouter、DeepSeek 官方…）|
| 存储 | Qdrant（向量）· PostgreSQL · Neo4j（引用图）· MinIO · Redis |
| 可观测 | Langfuse（全链路 trace）· Prometheus（/metrics）|

架构采用**六边形（Ports & Adapters）**：所有外部系统都抽象成接口，每个接口都有
真实实现和内存假实现——因此核心逻辑可在不依赖任何外部服务的情况下端到端测试，
更换后端只需替换一个 adapter。

---

## 快速开始（零依赖体验）

用内存假实现跑起来，不需要 Docker / GPU / 任何 API key，验证流程与界面：

```bash
# 后端（需要 uv：https://docs.astral.sh/uv/）
uv sync --extra dev
uv run pytest -q                              # 跑测试
uv run uvicorn apps.api.main:app --reload     # API → http://localhost:8000

# 前端（另开终端，需要 Node 18+）
cd apps/web && npm install && npm run dev     # 界面 → http://localhost:3000
```

此时问答链路（检索 → 生成 → 引用校验 → 前端角标）走的是假实现，答案是占位内容，
但整条流程是真实的。接上真实服务后即为可用系统。

---

## 真实部署（云 API，无需 GPU）

本机只跑数据库 + API + 前端，AI 能力全部走云：

```bash
# 1. 基础设施
docker compose -f deploy/docker-compose.yml up -d   # Postgres/Qdrant/Neo4j/MinIO/Redis

# 2. 配置
cp .env.example .env                                # 按下表填 key

# 3. 启动
export SL_USE_REAL_ADAPTERS=1 SL_USE_DB=1 SL_CACHE_ENABLED=1
uv run uvicorn apps.api.main:app --reload
uv run celery -A apps.worker.celery_app worker -l info   # 异步解析（另开终端）
cd apps/web && npm run dev
```

### 关键配置（`.env`，以 `SL_` 前缀覆盖）

| 用途 | 变量 | 说明 |
|---|---|---|
| LLM 网关 | `SL_LLM_API_BASE` `SL_LLM_API_KEY` | OpenAI 兼容网关（如 airouter）|
| 模型选择 | `SL_STRONG_MODEL` `SL_SMALL_MODEL` | 默认 `claude-opus-5-5` / `claude-haiku-5-5` |
| DeepSeek | `SL_DEEPSEEK_API_KEY` | 低价模型，配了就出现在模型选择器 |
| 向量化/重排 | `SL_SILICONFLOW_API_KEY` | 硅基流动 bge-m3 / bge-reranker |
| PDF 解析 | `SL_MINERU_API_TOKEN` | MinerU 云 API |
| 引用校验 | `SL_NLI_MODE` | `llm`（LLM 判官，默认）或 `deberta`（本地模型）|
| 存储 | `SL_USE_DB` `SL_DATABASE_URL` | `true` 用 Postgres 持久化 |
| 缓存 | `SL_CACHE_ENABLED` `SL_REDIS_URL` | `true` 开启 Redis 缓存 embedding |
| 可观测 | `SL_LANGFUSE_PUBLIC_KEY` `SL_LANGFUSE_SECRET_KEY` `SL_LANGFUSE_HOST` | 配了即自动上报 |
| 安全 | `SL_JWT_SECRET` `SL_BILLING_WEBHOOK_SECRET` | **上线前必须改成随机值** |

> 完整的分步接入（含 MinerU、模型下载、排错）见 [`docs/LOCAL_SETUP.md`](docs/LOCAL_SETUP.md)。

---

## 使用指南

所有接口需先登录拿 JWT，再以 `Authorization: Bearer <token>` 调用。

### 1. 注册 / 登录

```bash
curl -X POST localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"your-password"}'
# → { "access_token": "<JWT>", "user_id": "..." }
```

### 2. 导入文献

```bash
TOKEN=<上一步的 access_token>
curl -X POST localhost:8000/ingest/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F 'files=@paper.pdf'
# 解析 → 多粒度切分 → 向量化入库，返回 chunk 数
```

### 3. 快速问答（流式，带引用）

```bash
curl -N -X POST localhost:8000/query \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"question":"What is Position Interpolation?","model":"deepseek"}'
```
SSE 先流式返回 token，最后一条 `done` 事件带引用校验结果（每句的来源 `eid`、可信度）。
`model` 可选，不填用默认强模型；选了套餐不含的模型会返回 403。

### 4. 深度研究（多跳综述）

```bash
curl -N -X POST localhost:8000/research \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"question":"对比 RoPE 外推类方法在长文本上的表现"}'
```
SSE 推送研究过程（plan / research / reflect / write / verify）和最终综述。

### 5. 套餐与用量

```bash
curl localhost:8000/billing/overview -H "Authorization: Bearer $TOKEN"   # 当前套餐、配额剩余、累计成本
curl localhost:8000/billing/plans                                         # 套餐清单
curl -X POST localhost:8000/billing/checkout \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"plan_id":"pro"}'                                                   # 下单（返回订单号）
```

### 用界面

打开 `http://localhost:3000`：左栏管理知识库与套餐、中栏对话与研究过程、
右栏证据面板与引用图谱。顶部切换「快速问答 / 深度研究」，右上角选择模型。

### 跑评测

```bash
uv run python -m eval.cli path/to/dev.jsonl   # QASPER 风格的 {qid,question,gold_answer,...}
```

---

## 项目结构

```
scholarlens/
├── apps/
│   ├── api/       FastAPI：auth / ingest / query / research / papers / models / billing / eval
│   ├── worker/    Celery 离线解析流水线
│   └── web/       Next.js 前端（三栏界面、模型选择、引用图谱）
├── core/
│   ├── ports.py        外部系统的 Protocol 接口（六边形架构核心）
│   ├── adapters/       真实实现（MinerU/SiliconFlow/LiteLLM/Qdrant/Neo4j…）+ 内存 fakes
│   ├── domain.py       领域模型（Chunk / Query / Evidence / Claim）
│   ├── ingest/         解析产物 → PaperIR、去重
│   ├── index/          多粒度切分、Contextual Chunking、表格抽取、索引编排
│   ├── retrieval/      混合检索、RRF、重排、Query 路由
│   ├── agent/          深度研究协调器、覆盖度
│   ├── verify/         引用校验、重写
│   ├── llm/            模型目录、prompt、价格、用量
│   ├── auth/ billing/  登录鉴权、套餐、支付、计量
│   ├── db/ cache/      Postgres 存储、Redis 缓存
│   └── obs/            Langfuse 可观测
├── eval/          指标、消融矩阵、评测 runner
├── deploy/        docker-compose
└── tests/         118 个单测
```

---

## 测试

```bash
uv run pytest -q          # 118 个测试，全部用内存实现，无需外部服务
```

核心业务逻辑（检索、索引、引用校验、研究 Agent、计费、存储、缓存）均有单测覆盖；
数据库 SQL 用 SQLite 实跑验证；真实云 API（MinerU / 硅基流动 / Claude / DeepSeek /
Langfuse）均已在真实环境端到端验证。

---

## 实现状态

**已实现并验证**：文档解析、多粒度索引、混合检索与重排、深度研究 Agent、引用校验、
多模型选择、登录鉴权、套餐与配额、支付回调、token 成本计量、Postgres 存储、
Redis 缓存、可观测（Langfuse 全链路 span + Prometheus 指标）、前端三栏界面与评测框架。

**尚未完成**（后续增量）：

- `core/agent/graph.py` 的 LangGraph 绑定（研究协调器已可独立运行，仅缺 checkpoint /
  可中断的 LangGraph 封装）
- Qdrant / Neo4j / Postgres-RAG adapter 的真实服务联调（代码与接口契约已就绪）
- 前端 PDF 阅读器的 bbox 高亮（当前为占位）、知识库按 collection 的真实分组
- 真实支付网关对接（当前为签名校验骨架 + 模拟支付）

---

## License

待定。
