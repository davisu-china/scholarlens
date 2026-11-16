"""按内容做幂等去重（PRD 第 06 章：按文件 SHA-256 实现幂等）。"""

from __future__ import annotations

import hashlib


def content_hash(data: bytes) -> str:
    """文件内容的 SHA-256 十六进制串。相同内容 → 相同 id，天然去重。"""
    return hashlib.sha256(data).hexdigest()


def paper_id_from_bytes(data: bytes, *, prefix_len: int = 16) -> str:
    """从文件内容派生内部 paper_id（取 SHA-256 前缀）。"""
    return content_hash(data)[:prefix_len]


class SeenRegistry:
    """已见内容登记表的抽象（真实实现查 Postgres；这里给内存版）。"""

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_duplicate(self, data: bytes) -> bool:
        return content_hash(data) in self._seen

    def register(self, data: bytes) -> str:
        h = content_hash(data)
        self._seen.add(h)
        return h
