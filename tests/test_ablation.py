from core.adapters.fakes import FakeLLM
from core.container import build_container
from eval.ablation import ABLATION_MATRIX, run_ablation
from eval.dataset import EvalExample


def test_matrix_is_monotonic():
    # 每一行开启的组件数应不少于上一行（逐步叠加）
    counts = [sum([c.layout_parse, c.contextual_chunk, c.hybrid, c.rerank, c.verify, c.agent])
              for c in ABLATION_MATRIX]
    assert counts == sorted(counts)
    assert ABLATION_MATRIX[0].name.startswith("B0")


async def test_run_ablation_smoke(paper):
    async def build_qa(cfg):
        c = build_container()
        await c.indexer.index_paper(paper)
        c.qa._llm = FakeLLM(responses=["YaRN lower perplexity at 128K [e0]."] * 5)
        c.verifier._llm = c.qa._llm
        return c.qa

    examples = [EvalExample(qid="1", question="yarn perplexity",
                            gold_answer="YaRN lower perplexity at 128K")]
    rows = await run_ablation(build_qa, examples, matrix=ABLATION_MATRIX[:2])
    assert len(rows) == 2
    assert rows[0].report.suite.startswith("B0")
