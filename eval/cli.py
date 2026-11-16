"""评测 CLI：make eval SUITE=path/to/dev.jsonl

用内存 fakes 跑通流程做冒烟；接真实 adapter 时换 build_real_container。
"""

from __future__ import annotations

import asyncio
import sys

from core.container import build_container
from eval.dataset import load_jsonl
from eval.runner import run_suite


async def _main(path: str) -> None:
    examples = load_jsonl(path)
    container = build_container()
    report = await run_suite(container.qa, examples, suite=path)
    print(report.to_row())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m eval.cli <dev.jsonl>")
        raise SystemExit(1)
    asyncio.run(_main(sys.argv[1]))
