"""词法稀疏编码器：把文本编码成 {token_id: weight} 的稀疏向量，供 Qdrant sparse 检索。

当向量化走云 API（只返回 dense）时，用它补上 sparse 这一路。采用 BM25 的 term 权重
思想的文档侧近似：权重 = 词频的饱和函数，token_id 用稳定哈希。这样无需全局语料统计即可
为每个文档独立编码，重点保证"专有名词精确匹配"（模型名、数据集名、公式符号）。

与查询侧对称：查询也用同一编码器，Qdrant 对两个 sparse 向量做点积即得词法匹配分。
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*")
_SPARSE_DIM = 1 << 20  # 哈希空间，碰撞概率可忽略


def _token_id(token: str) -> int:
    return int(hashlib.md5(token.encode()).hexdigest(), 16) % _SPARSE_DIM


class LexicalSparseEncoder:
    def __init__(self, *, k1: float = 1.5) -> None:
        self._k1 = k1

    def encode(self, text: str) -> dict[int, float]:
        tokens = _TOKEN.findall(text.lower())
        if not tokens:
            return {}
        weights: dict[int, float] = {}
        for token, tf in Counter(tokens).items():
            # BM25 的 tf 饱和：tf*(k1+1)/(tf+k1)，弱化高频词、保留是否出现的信号
            weights[_token_id(token)] = tf * (self._k1 + 1) / (tf + self._k1)
        return weights
