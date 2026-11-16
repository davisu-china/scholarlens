import { streamSSE } from "./sse";
import { authHeaders } from "./auth";
import type { QADone, ResearchAnswer, TraceEvent } from "./types";

/** 快速问答：回调逐 token，结束时回调一次 done(含引用与证据)。 */
export async function askQuestion(
  question: string,
  opts: { collection?: string; model?: string | null; onToken: (t: string) => void; onDone: (d: QADone) => void },
): Promise<void> {
  for await (const ev of streamSSE("/api/query", {
    method: "POST",
    headers: await authHeaders(),
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
    headers: await authHeaders(),
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
  const r = await fetch("/api/models", { headers: await authHeaders() });
  return r.json() as Promise<{ default: string | null; plan: string; models: { id: string; label: string; description: string; tier: string; locked: boolean }[] }>;
}

export async function fetchBilling() {
  const r = await fetch("/api/billing/overview", { headers: await authHeaders() });
  return r.json() as Promise<{
    plan: { id: string; name: string; price_cny_per_month: number };
    quotas: { action: string; window: string; limit: number; used: number; remaining: number }[];
    usage: { by_action: Record<string, number>; by_model: Record<string, number>; cost_cny: number };
  }>;
}

export async function upgradePlan(planId: string) {
  const h = { "Content-Type": "application/json", ...(await authHeaders()) };
  const order = await (await fetch("/api/billing/checkout", {
    method: "POST", headers: h, body: JSON.stringify({ plan_id: planId }),
  })).json();
  // 雏形：直接触发模拟支付；生产跳转 order.pay_url 由网关回调
  await fetch(`/api/billing/simulate-payment/${order.order_id}`, { method: "POST" });
}

export async function downgradeFree() {
  // 免费套餐无需支付，雏形下单接口会拒绝；降级在生产由订阅到期处理。
  // 这里演示用：直接下单 pro 的反向——省略，UI 只在付费态提供“查看用量”。
}

export async function fetchCollections() {
  const r = await fetch("/api/papers/collections", { headers: await authHeaders() });
  return r.json() as Promise<{ name: string; count: number }[]>;
}

export async function fetchPapers(collection?: string) {
  const q = collection ? `?collection=${encodeURIComponent(collection)}` : "";
  const r = await fetch(`/api/papers${q}`, { headers: await authHeaders() });
  return r.json() as Promise<{ paper_id: string; title: string; collection: string; n_chunks: number; year: number | null }[]>;
}

// PDF 带鉴权取回后生成临时 URL（react-pdf 用）
export async function fetchPdfUrl(paperId: string): Promise<string> {
  const r = await fetch(`/api/papers/${paperId}/pdf`, { headers: await authHeaders() });
  if (!r.ok) throw new Error("pdf not found");
  return URL.createObjectURL(await r.blob());
}
