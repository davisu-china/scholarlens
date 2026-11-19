"""ScholarLens API 的启动入口（Windows 专用）。

为什么需要这个文件：
- 项目用 psycopg 的异步模式连接 PostgreSQL。
- Windows 上 asyncio 默认使用 ProactorEventLoop，psycopg 不支持，
  后端启动时会抛 InterfaceError。
- 这里显式创建 SelectorEventLoop 再启动 uvicorn，绕开该限制。

为什么不用 `uvicorn apps.api.main:app`：
uvicorn 会自己创建事件循环，外部设置 event loop policy 来不及生效；
只有自己创建 loop，才能保证 psycopg 运行在 SelectorEventLoop 上。

启动方式（在项目根目录，先在终端设置三个环境变量：
SL_USE_REAL_ADAPTERS=1、SL_USE_DB=1、SL_CACHE_ENABLED=1）：

    uv run python run_api.py

注意：
- 不带热重载，适合上传/解析这类不能中途重启的场景。
- 在 Linux/macOS 上没有这个问题，直接使用 uvicorn 命令即可。
"""

import asyncio
import selectors

import uvicorn


def main() -> None:
    # 加载 ASGI 应用并准备 uvicorn 服务器配置
    config = uvicorn.Config("apps.api.main:app", host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)

    # 强制使用 SelectorEventLoop（Windows 上 psycopg 异步只支持它）
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)

    # 运行完整的 ASGI 生命周期：startup → 处理请求 → shutdown
    loop.run_until_complete(server.serve())


if __name__ == "__main__":
    main()