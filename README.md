# ScholarLens · 可溯源的学术深度研究引擎

> 面向学术文献的深度研究引擎：解析论文、多粒度索引、混合检索与重排，由 LangGraph Agent 编排生成**句级可溯源**的研究综述——每一条结论都能回溯到原文的页码与坐标框。

## 项目简介

ScholarLens 针对学术研究中的三个痛点：

- **解析失真**——PDF 转文本丢失版式、公式、图表结构；
- **单跳检索不够**——复杂问题需要多跳、跨文献推理；
- **引用不可信**——LLM 生成的综述常出现无据结论（幻觉）。

通过文档解析流水线、多粒度索引、混合检索 + 重排、深度研究 Agent、引用校验与反幻觉模块，输出可信、可复现、可溯源的研究结果。

## 设计目标

> 以下为设计目标值，最终以评测框架的实测数据为准。

| 维度 | 目标 | 衡量方式 |
|---|---|---|
| 检索质量 | 证据段召回率比朴素向量检索提升 ≥ 25% | QASPER evidence Recall@10，消融实验 |
| 答案可信 | 引用准确率 ≥ 0.90，无据结论 < 5% | NLI 自动校验 + 人工抽检 |
| 研究效率 | 生成 3000 字综述 < 3 分钟 | 端到端计时，LangSmith / Langfuse trace |
| 工程质量 | 一键部署、可观测、可复现评测 | — |

## 技术栈

- **语言**：Python 3.12 全栈
- **后端**：FastAPI
- **前端**：Next.js 14 + TypeScript + Tailwind + shadcn/ui
- **Agent 编排**：LangGraph 状态机
- **可观测**：LangSmith / Langfuse
- **溯源**：句级引用，精确到页码和坐标框

## 文档

## 项目结构（monorepo）

```
scholarlens/
├── apps/
│   ├── api/       FastAPI：路由、鉴权、SSE（/ingest /query /research /papers /eval）
│   ├── worker/    Celery：解析、切分、Embedding 的离线流水线
│   └── web/       Next.js + shadcn/ui 前端（三栏界面、PDF bbox 高亮、引用图谱）
├── core/
│   ├── ports.py   所有外部系统的 Protocol 接口（六边形架构）
│   ├── adapters/  真实实现(Qdrant/Neo4j/LiteLLM/BGE/DeBERTa/MinerU) + 内存 fakes
│   ├── domain.py  跨模块领域模型（Chunk/Query/Evidence/Claim）
│   ├── container.py 组装根：fakes 默认、真实 adapter 可替换
│   ├── ingest/    解析器适配层 → PaperIR（Document IR）+ SHA-256 去重
│   ├── index/     多粒度索引、Contextual Chunking、表格抽取、索引编排
│   ├── retrieval/ 混合检索、RRF、重排、Query 路由
│   ├── agent/     深度研究协调器(Plan→Research→Reflect→Write→Verify)、覆盖度
│   ├── verify/    NLI 引用校验、重写、span 定位
│   ├── qa.py      快速问答服务（流式 + 拒答）
│   └── llm/       prompt 模板（LiteLLM adapter 在 adapters/）
├── eval/          数据集加载器、指标、消融矩阵、CLI
├── deploy/        docker-compose.yml（Postgres/Qdrant/Neo4j/MinIO/Redis）
└── tests/         55 个单测，全绿
```

## 架构：六边形（Ports & Adapters）

所有外部系统（向量库 / 图库 / Embedder / Reranker / LLM / NLI / 解析器 / 表格库 /
对象存储）都抽象为 `core/ports.py` 的 Protocol。每个 port 有两种实现：

- **真实 adapter**（`core/adapters/`）：Qdrant、Neo4j、LiteLLM、BGE-M3、bge-reranker、
  DeBERTa-NLI、MinerU、Postgres、MinIO；
- **内存 fake**（`core/adapters/fakes.py`）：让整条问答 / 研究链路**不依赖 GPU/Docker/
  模型**即可端到端运行与测试。

换后端只改一个 adapter，业务逻辑零改动。默认 `build_container()` 用 fakes（开箱即跑），
设 `SL_USE_REAL_ADAPTERS=1` 切换到 `build_real_container()`。

## 本地开发

**零依赖快速体验**（用 fakes，后端开箱即跑，无需 Docker / GPU / 模型）：

```bash
uv sync --extra dev
uv run pytest -q                                   # 55 个测试
uv run uvicorn apps.api.main:app --reload          # :8000，/query /research 直接可用
cd apps/web && npm install && npm run dev          # :3000
```

**接真实后端**：

```bash
docker compose -f deploy/docker-compose.yml up -d  # Postgres/Qdrant/Neo4j/MinIO/Redis
cp .env.example .env                               # 填 LLM API key 等
export SL_USE_REAL_ADAPTERS=1
uv run uvicorn apps.api.main:app --reload
uv run celery -A apps.worker.celery_app worker -l info
```

> 核心业务逻辑已实现并测试（检索 / 索引 / 引用校验 / 研究 Agent / 评测，55 测试全绿）。
> 真实 adapter（Qdrant/Neo4j/LiteLLM/BGE/DeBERTa/MinerU）照 port 实现、结构契约已测；
> 其与模型、GPU、外部服务的联调需在本地环境完成。

## 文档

完整的 PRD 与技术实现文档见 [`docs/ScholarLens_PRD_Tech.html`](docs/ScholarLens_PRD_Tech.html)，涵盖：

- **Part I 产品需求**：项目概述、目标用户与场景、功能需求、交互与页面、非功能指标
- **Part II 技术实现**：系统架构、文档解析流水线、多粒度索引、混合检索与重排、深度研究 Agent、引用校验与反幻觉、评测体系、技术栈与工程
- **Part III 交付**：风险与对策、面试亮点

## 状态

核心功能已实现并测试（六边形架构，fakes 下端到端可跑，55 测试全绿；前端 `next build` 通过）。
真实 adapter 的外部服务联调待本地环境完成。

## License

待定。
