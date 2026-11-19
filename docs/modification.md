# 修改说明

日期：2026-11-19

本文档记录在 ScholarLens MVP 端到端验证过程中所做的修改、修改原因，以及合并后需要执行的操作。

改动分为五个部分：

1. 按文献库过滤
2. 上下文前缀性能
3. 表格入库幂等
4. Windows 下的 API 启动入口
5. npm lockfile 地址规范化

---

## 1. 按文献库过滤

### 问题

collection 过滤在两种向量库实现中都不生效：

- Qdrant payload 的 `collection` 字段实际写的是 `chunk.provenance.paper_id`
- 内存 fake 向量库完全忽略了 `collection` 过滤条件
- `Indexer.index_paper` 没有接收上传时选择的 collection

结果是：带 `"collection": "<库名>"` 的查询永远召回不到任何证据，API 直接拒答。

### 改动

| 文件 | 改动 |
|---|---|
| `core/domain.py` | `Chunk` 新增 `collection` 字段（默认空字符串）。 |
| `core/index/indexer.py` | `index_paper(paper, *, collection="default")` 会规范化库名，并在向量化/入库前写入每个 chunk。 |
| `core/adapters/qdrant_store.py` | payload 使用 `chunk.collection or "default"`，不再写 `paper_id`。 |
| `core/adapters/fakes.py` | `_match_filters` 增加了 collection 条件。 |
| `apps/api/routers/ingest.py` | 把上传表单里的 `collection` 传给 `index_paper`。 |
| `tests/test_index.py` | 新增 `test_indexer_filters_by_collection`。 |

### 改完后的行为

- `POST /query` 带上 `collection` 时，只在该文献库内检索。
- 查询不存在的文献库时，返回空证据和正常的拒答提示。
- `GET /papers?collection=...` 继续通过论文登记表正常工作。

### 迁移

已有的 Qdrant 点仍然带着旧的 `collection` payload。部署后需要重新导入相关论文；由于 chunk id 是确定性的，新数据会覆盖旧点。

---

## 2. 上下文前缀性能

### 问题

上下文前缀会为每个 L2 chunk 调用一次 LLM，原实现是串行执行。这篇五页论文共有 43 个 L2 chunk，也就是 43 次串行调用。

测试论文上的实测结果：

| 模型 | 成功数（10 次样本） | 中位延迟 |
|---|---|---|
| `deepseek-v4-pro`（strong） | 8/10 | 15.1 秒 |
| `deepseek-chat`（cheap） | 10/10 | 1.0 秒 |

在 30 秒单次超时下，strong 模型约有一半调用超时。上传总耗时约 402 秒，大量前缀为空。

### 改动

| 文件 | 改动 |
|---|---|
| `core/index/chunker.py` | `_add_context` 改为 `asyncio.Semaphore` + `asyncio.gather`，支持可配置并发；每次调用用 `asyncio.wait_for` 设置超时；单个 chunk 失败不影响其他 chunk；构造函数新增 `model` 参数。 |
| `core/index/indexer.py` | 新增 `context_model` 参数，并传给 chunker。 |
| `core/container.py` | 传入 `context_model=small_model`，前缀生成改用 cheap 模型。 |
| `core/config.py` | 新增 `contextual_chunk`、`contextual_concurrency`、`contextual_timeout`。 |
| `.env.example` | 补充 `SL_CONTEXTUAL_CHUNK`、`SL_CONTEXTUAL_CONCURRENCY`、`SL_CONTEXTUAL_TIMEOUT`。 |

默认配置：

```
SL_CONTEXTUAL_CHUNK=true
SL_CONTEXTUAL_CONCURRENCY=5
SL_CONTEXTUAL_TIMEOUT=30
```

### 改完后的行为

- 前缀生成最多同时发起 5 个请求。
- 前缀生成使用 cheap 模型；回答生成和表格抽取仍然使用 strong 模型。
- 单次调用失败只是该 chunk 的前缀为空，不会导致上传失败。

### 重新索引

前缀是在入库时写入的。需要重新导入论文才能重新生成。

---

## 3. 表格入库幂等

### 问题

`result_rows` 原本只做追加插入。同一篇论文重复导入时，所有表格行都会重复（例如 84 行变成 168、252）。

其他存储层本身已经是幂等的：

- Qdrant 用确定性 chunk id 覆盖写入
- 论文登记表按 `paper_id` 覆盖
- 对象存储按 key 覆盖

只有表格库不是。

### 改动

| 文件 | 改动 |
|---|---|
| `core/ports.py` | `TableStore` 新增 `delete_by_paper`。 |
| `core/adapters/postgres_tables.py` | 按 `paper_id` 删除行。 |
| `core/adapters/fakes.py` | 内存实现按 `paper_id` 过滤。 |
| `core/index/indexer.py` | 入库前先删除该论文的旧行，再抽取和插入新行。 |
| `tests/test_index.py` | 新增 `test_reindex_replaces_table_rows`。 |

### 改完后的行为

- 重新索引是“替换”而不是“追加”。
- `n_table_rows` 反映本次抽取的行数，不再是累计值。

### 已有重复数据

重新导入某篇论文会自动清掉它的旧行。对不再重新导入的论文，可以用下面的 SQL 去重：

```sql
DELETE FROM result_rows a
USING result_rows b
WHERE a.id > b.id
  AND a.paper_id = b.paper_id
  AND a.block_id = b.block_id
  AND a.method = b.method
  AND a.dataset = b.dataset
  AND a.metric = b.metric
  AND a.value = b.value;
```

---

## 4. Windows 下的 API 启动入口

`run_api.py` 用显式的 `SelectorEventLoop` 启动 uvicorn。

为什么需要它：

- 项目通过 psycopg 的异步接口连接 PostgreSQL。
- Windows 上 asyncio 默认使用 `ProactorEventLoop`，psycopg 不支持，启动时会报
  `Psycopg cannot use the 'ProactorEventLoop'`。
- 在 `uvicorn.run` 之前设置事件循环策略不够，因为 uvicorn 会自己创建循环；
  只有显式创建 loop 才能解决。

使用方式（在项目根目录）：

```
uv run python run_api.py
```

环境变量需要在同一个终端里设置，例如：

```
SL_USE_REAL_ADAPTERS=1
SL_USE_DB=1
SL_CACHE_ENABLED=1
```

在 Linux 和 macOS 上不需要这个文件，直接使用 uvicorn 命令即可。

---

## 5. npm lockfile 地址规范化

原始的 `apps/web/package-lock.json` 中有 161 个下载地址指向
`mirrors.tencentyun.com`。这是内网镜像，外部网络无法解析，安装时会报
`getaddrinfo ENOTFOUND`。

这些地址已替换为 `https://registry.npmjs.org/`。包名、版本号和完整性哈希都没有改动。

本地备份 `apps/web/package-lock.json.bak` 保留在磁盘上，但已加入 `.gitignore`，不会提交。

---

## 测试状态

使用内存存储时：

```
SL_USE_DB=false uv run pytest -q
# 133 passed
```

如果不加这个覆盖，本地 `.env` 中的 `SL_USE_DB=true` 会导致 10 个 API 测试在 Windows 上失败，因为测试客户端运行在 Proactor 事件循环上。没有本地 `.env` 的 CI 环境默认 `SL_USE_DB=false`，不受影响。

---

## 修改的文件

核心：

- `core/config.py`
- `core/domain.py`
- `core/ports.py`
- `core/index/chunker.py`
- `core/index/indexer.py`
- `core/container.py`
- `core/adapters/qdrant_store.py`
- `core/adapters/fakes.py`
- `core/adapters/postgres_tables.py`

API：

- `apps/api/routers/ingest.py`

测试：

- `tests/test_index.py`

配置与工具：

- `.env.example`
- `.gitignore`
- `apps/web/package-lock.json`
- `run_api.py`

仅本地保留（已被 `.gitignore` 排除，不提交）：

- `diag_llm.py`
- `diag_prefix.py`
- `q.json`
- `apps/web/package-lock.json.bak`
- `paper.pdf`、`paper2.pdf`

---

## 已知限制与后续事项

- collection 只是文献库名称，不是租户边界；所有用户仍然共享同一个向量集合。
- `POST /ingest/upload` 仍然是同步的。长论文可能要几分钟，API 没有使用 Celery worker。
- MinIO 仍未接入真实容器，论文登记表也还是内存实现；重启后 PDF 和文献库元数据会丢失，但 Qdrant 向量还在。
- 引用图仍然没有边，因为 MinerU 返回的参考文献没有 Semantic Scholar id。
- 回答生成和表格抽取仍然使用 strong 模型。
