"""真实 NLI adapter：DeBERTa-v3-large-MNLI，计算 P(前提蕴含假设)。

实现 core.ports.NLIModel。⚠️ 需下载模型（GPU 更快），无法在沙箱里运行。
"""

from __future__ import annotations

from core.config import settings


class DebertaNLI:
    def __init__(self, model_name: str | None = None, *, batch_size: int = 32) -> None:
        self._model_name = model_name or settings.nli_model
        self._batch_size = batch_size
        self._pipe = None
        self._entail_idx = None

    def _ensure(self):
        if self._pipe is None:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
            import torch

            self._tok = AutoTokenizer.from_pretrained(self._model_name)
            self._model = AutoModelForSequenceClassification.from_pretrained(self._model_name)
            self._model.eval()
            self._torch = torch
            # 找到 "entailment" 标签的下标（不同模型标签顺序不同）
            labels = self._model.config.id2label
            self._entail_idx = next(i for i, name in labels.items() if "entail" in name.lower())
        return self._model

    async def entailment(self, pairs: list[tuple[str, str]]) -> list[float]:
        self._ensure()
        torch = self._torch
        probs: list[float] = []
        for i in range(0, len(pairs), self._batch_size):
            batch = pairs[i : i + self._batch_size]
            premises = [p for p, _ in batch]
            hypotheses = [h for _, h in batch]
            inputs = self._tok(premises, hypotheses, return_tensors="pt", padding=True, truncation=True)
            with torch.no_grad():
                logits = self._model(**inputs).logits
            p = torch.softmax(logits, dim=-1)[:, self._entail_idx]
            probs.extend(float(x) for x in p)
        return probs
