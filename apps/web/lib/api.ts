const USER_HEADER = { "X-User-Id": "demo" };

import { streamSSE } from "./sse";
import type { QADone, ResearchAnswer, TraceEvent } from "./types";

/** 快速问答：回调逐 token，结束时回调一次 done(含引用与证据)。 */
export async function askQuestion(
  question: string,
  opts: { collection?: string; model?: string | null; onToken: (t: string) => void; onDone: (d: QADone) => void },
): Promise<void> {
  for await (const ev of streamSSE("/api/query", {
    method: "POST",
    headers: USER_HEADER,
    body: JSON.stringify({ question, collection: opts.collection, model: opts.model }),
  })) {
    if (ev.event === "token") opts.onToken(ev.data);
    else if (ev.event === "done") opts.onDone(JSON.parse(ev.data) as QADone);
  }
}

/** 深度研究：回调每个 trace 步骤，结束时回调最终答案。 */
export async function deepResearch(
  question: string,
  opts: { approvedPlan?: string[]; model?: string | null; onTrace: (e: TraceEvent) => void; onAnswer: (a: ResearchAnswer) => void },
): Promise<void> {
  for await (const ev of streamSSE("/api/research", {
    method: "POST",
    headers: USER_HEADER,
    body: JSON.stringify({ question, approved_plan: opts.approvedPlan, model: opts.model }),
  })) {
    if (ev.event === "answer") opts.onAnswer(JSON.parse(ev.data) as ResearchAnswer);
    else opts.onTrace({ kind: ev.event, data: JSON.parse(ev.data || "{}") });
  }
}

export async function fetchCitationGraph(paperId: string) {
  const r = await fetch(`/api/papers/${paperId}/citations`);
  return r.json() as Promise<{ nodes: { id: string; seed?: boolean }[]; edges: { source: string; target: string }[] }>;
}

export async function fetchModels() {
  const r = await fetch("/api/models", { headers: USER_HEADER });
  return r.json() as Promise<{ default: string | null; plan: string; models: { id: string; label: string; description: string; tier: string; locked: boolean }[] }>;
}

export async function fetchBilling() {
  const r = await fetch("/api/billing/overview", { headers: USER_HEADER });
  return r.json() as Promise<{
    plan: { id: string; name: string; price_cny_per_month: number };
    quotas: { action: string; window: string; limit: number; used: number; remaining: number }[];
    usage: { by_action: Record<string, number>; by_model: Record<string, number>; cost_cny: number };
  }>;
}

export async function setPlan(planId: string) {
  await fetch("/api/billing/plan", {
    method: "POST", headers: { "Content-Type": "application/json", ...USER_HEADER },
    body: JSON.stringify({ plan_id: planId }),
  });
}
