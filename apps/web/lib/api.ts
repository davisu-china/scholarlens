import { streamSSE } from "./sse";
import type { QADone, ResearchAnswer, TraceEvent } from "./types";

/** 快速问答：回调逐 token，结束时回调一次 done(含引用与证据)。 */
export async function askQuestion(
  question: string,
  opts: { collection?: string; onToken: (t: string) => void; onDone: (d: QADone) => void },
): Promise<void> {
  for await (const ev of streamSSE("/api/query", {
    method: "POST",
    body: JSON.stringify({ question, collection: opts.collection }),
  })) {
    if (ev.event === "token") opts.onToken(ev.data);
    else if (ev.event === "done") opts.onDone(JSON.parse(ev.data) as QADone);
  }
}

/** 深度研究：回调每个 trace 步骤，结束时回调最终答案。 */
export async function deepResearch(
  question: string,
  opts: { approvedPlan?: string[]; onTrace: (e: TraceEvent) => void; onAnswer: (a: ResearchAnswer) => void },
): Promise<void> {
  for await (const ev of streamSSE("/api/research", {
    method: "POST",
    body: JSON.stringify({ question, approved_plan: opts.approvedPlan }),
  })) {
    if (ev.event === "answer") opts.onAnswer(JSON.parse(ev.data) as ResearchAnswer);
    else opts.onTrace({ kind: ev.event, data: JSON.parse(ev.data || "{}") });
  }
}

export async function fetchCitationGraph(paperId: string) {
  const r = await fetch(`/api/papers/${paperId}/citations`);
  return r.json() as Promise<{ nodes: { id: string; seed?: boolean }[]; edges: { source: string; target: string }[] }>;
}
