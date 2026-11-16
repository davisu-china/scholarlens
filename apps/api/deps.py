"""FastAPI 依赖：提供应用容器。

默认用 fakes（开箱即跑、便于演示）。设置 SL_USE_REAL_ADAPTERS=1 时接真实后端
（见 core/adapters/real.py 的 build_real_container）。
"""

from __future__ import annotations

import os
from functools import lru_cache

from core.config import settings
from core.container import Container, build_container


@lru_cache
def get_container() -> Container:
    if os.getenv("SL_USE_REAL_ADAPTERS") == "1":
        from core.adapters.real import build_real_container

        return build_real_container()
    # fakes 模式下，只要配置了 MinerU token，PDF 解析就走真实云 API
    parser = None
    if settings.mineru_api_token:
        from core.adapters.mineru_cloud import MinerUCloudParser

        parser = MinerUCloudParser()
    return build_container(parser=parser)
