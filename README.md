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
│   ├── ingest/    解析器适配层 → PaperIR（Document IR）
│   ├── index/     多粒度索引、Contextual Chunking、表格抽取
│   ├── retrieval/ 混合检索、RRF、重排、Query 路由
│   ├── agent/     LangGraph 研究图、工具定义
│   ├── verify/    NLI 引用校验、span 定位
│   └── llm/       LiteLLM 封装、prompt 模板
├── eval/          数据集加载器、指标、消融脚本
├── deploy/        docker-compose.yml（Postgres/Qdrant/Neo4j/MinIO/Redis）
└── tests/
```

## 本地开发

```bash
# 0. 基础设施（需要 Docker）
docker compose -f deploy/docker-compose.yml up -d

# 1. 后端（需要 uv）
cp .env.example .env
uv sync --extra dev
uv run uvicorn apps.api.main:app --reload --port 8000
uv run celery -A apps.worker.celery_app worker -l info   # 另开一个终端

# 2. 前端（需要 Node 18+）
cd apps/web && npm install && npm run dev   # http://localhost:3000
```

> 当前 `core/*` 与各路由是带完整接口签名的骨架（`NotImplementedError` + TODO），
> `PaperIR` schema 和 RRF 融合已是可用实现。按 PRD 第 07–12 章逐模块填充。

## 文档

完整的 PRD 与技术实现文档见 [`docs/ScholarLens_PRD_Tech.html`](docs/ScholarLens_PRD_Tech.html)，涵盖：

- **Part I 产品需求**：项目概述、目标用户与场景、功能需求、交互与页面、非功能指标
- **Part II 技术实现**：系统架构、文档解析流水线、多粒度索引、混合检索与重排、深度研究 Agent、引用校验与反幻觉、评测体系、技术栈与工程
- **Part III 交付**：风险与对策、面试亮点

## 状态

🚧 开发中。

## License

待定。
