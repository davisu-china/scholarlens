import { streamSSE } from "./sse";
import { ApiError, authFetch, readError } from "./auth";
import type {
  BillingOverview, Collection, ModelInfo, Paper, Plan, QADone, ResearchAnswer, TraceEvent,
} from "./types";

async function getJSON<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await authFetch(url, init);
  if (!r.ok) throw await readError(r);
  return r.json() as Promise<T>;
}

const post = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

type Scope = { collection?: string | null; model?: string | null; signal?: AbortSignal };

/** 快速问答：回调逐 token，结束时回调一次 done（含引用校验与证据）。 */
export async function askQuestion(
  question: string,
  opts: Scope & { onToken: (t: string) => void; onDone: (d: QADone) => void },
): Promise<void> {
  const body = { question, collection: opts.collection ?? undefined, model: opts.model ?? undefined };
  for await (const ev of streamSSE("/api/query", { ...post(body), signal: opts.signal })) {
    if (ev.event === "token") opts.onToken(ev.data);
    else if (ev.event === "done") opts.onDone(JSON.parse(ev.data) as QADone);
  }
}

/** 深度研究第一步：生成研究计划，等待用户确认。 */
export function planResearch(question: string, opts: Scope) {
  const body = { question, collection: opts.collection ?? undefined, model: opts.model ?? undefined };
  return getJSON<{ thread_id: string; plan: string[] }>("/api/research/plan", { ...post(body), signal: opts.signal });
}

/** 深度研究第二步：按确认后的计划执行，推送过程与最终综述。 */
export async function resumeResearch(
  threadId: string,
  approvedPlan: string[],
  opts: { signal?: AbortSignal; onTrace: (e: TraceEvent) => void; onAnswer: (a: ResearchAnswer) => void },
): Promise<void> {
  const init = { ...post({ thread_id: threadId, approved_plan: approvedPlan }), signal: opts.signal };
  for await (const ev of streamSSE("/api/research/resume", init)) {
    if (ev.event === "answer") {
      opts.onAnswer(JSON.parse(ev.data) as ResearchAnswer);
    } else {
      const data = JSON.parse(ev.data || "{}") as Record<string, unknown>;
      opts.onTrace({ kind: ev.event, detail: String(data.detail ?? ""), data });
    }
  }
}

export const fetchModels = () =>
  getJSON<{ default: string | null; plan: string; models: ModelInfo[] }>("/api/models");

export const fetchBilling = () => getJSON<BillingOverview>("/api/billing/overview");

export const fetchPlans = () => getJSON<Plan[]>("/api/billing/plans");

export async function upgradePlan(planId: string): Promise<void> {
  const order = await getJSON<{ order_id: string }>("/api/billing/checkout", post({ plan_id: planId }));
  // 目前后端是模拟支付：下单后直接触发一次支付成功回调。接入真实网关后改为跳转 pay_url。
  const r = await fetch(`/api/billing/simulate-payment/${order.order_id}`, { method: "POST" });
  if (!r.ok) throw await readError(r);
}

export const fetchCollections = () => getJSON<Collection[]>("/api/papers/collections");

export const fetchPapers = () => getJSON<Paper[]>("/api/papers");

export const fetchCitationGraph = (paperId: string) =>
  getJSON<{ nodes: { id: string; seed?: boolean }[]; edges: { source: string; target: string }[] }>(
    `/api/papers/${encodeURIComponent(paperId)}/citations`,
  );

/** PDF 带鉴权取回后生成临时 URL（react-pdf 用）。调用方负责 revoke。 */
export async function fetchPdfUrl(paperId: string): Promise<string> {
  const r = await authFetch(`/api/papers/${encodeURIComponent(paperId)}/pdf`);
  if (!r.ok) throw new ApiError(r.status, r.status === 404 ? "这篇论文的原文文件不在库里" : "原文加载失败");
  return URL.createObjectURL(await r.blob());
}

/** 上传并解析一篇 PDF。一次一个文件，便于逐个显示状态。 */
export async function uploadPaper(file: File, collection: string): Promise<Paper> {
  const form = new FormData();
  form.append("files", file);
  form.append("collection", collection);
  const r = await authFetch("/api/ingest/upload", { method: "POST", body: form });
  if (!r.ok) throw await readError(r);
  const [p] = (await r.json()) as Paper[];
  return p;
}

/** 把错误转成给用户看的说明。 */
export function describeError(e: unknown): { message: string; status: number } {
  if (e instanceof ApiError) {
    if (e.status === 429) return { status: 429, message: e.message || "当前套餐的额度已用完" };
    if (e.status === 403) return { status: 403, message: e.message || "当前套餐不包含所选模型" };
    if (e.status === 502 || e.status === 504) return { status: e.status, message: "服务暂时没有响应，请稍后重试" };
    if (e.status >= 500) return { status: e.status, message: e.message.length < 200 ? e.message : "服务出错了，请稍后重试" };
    return { status: e.status, message: e.message };
  }
  return { status: 0, message: "连接中断了，请重试" };
}
