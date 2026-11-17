// 与后端 API 对齐的类型（见 core/domain.py、apps/api/routers）。

export interface BBox { page: number; x0: number; y0: number; x1: number; y1: number }

export interface Provenance {
  paper_id: string;
  block_id: string;
  bboxes: BBox[];
}

export interface Evidence {
  id: string;
  text: string;
  score: number;
  provenance: Provenance;
  section_path: string[];
}

export interface Claim {
  text: string;
  eids: string[];
  supported: boolean;
  best_eid: string | null;
  span: Provenance | null;
}

export interface QADone {
  trust: number;
  claims: Claim[];
  evidence?: Record<string, Evidence>;
}

export interface TraceEvent {
  kind: string; // plan / research / reflect / write / verify
  detail: string;
  data: Record<string, unknown>;
}

export interface ResearchAnswer {
  answer: string;
  trust: number;
  claims: Claim[];
  coverage: number;
  evidence?: Record<string, Evidence>;
}

export interface Paper {
  paper_id: string;
  title: string;
  collection: string;
  n_chunks: number;
  year: number | null;
}

export interface Collection { name: string; count: number }

export interface ModelInfo { id: string; label: string; description: string; tier: string; locked: boolean }

export interface QuotaRow { action: string; window: string; limit: number | null; used: number; remaining: number | null }

export interface BillingOverview {
  plan: { id: string; name: string; price_cny_per_month: number };
  quotas: QuotaRow[];
  usage: { by_action: Record<string, number>; by_model: Record<string, number>; cost_cny: number };
}

export interface Plan {
  id: string;
  name: string;
  price_cny_per_month: number;
  allowed_models: string[];
  quotas: Record<string, { per_day: number | null; per_month: number | null }>;
}

export type Mode = "qa" | "research";

export type AssistantStatus =
  | "planning"   // 深度研究：正在生成计划
  | "plan"       // 深度研究：等待用户确认计划
  | "running"    // 深度研究：检索、阅读、写作中
  | "streaming"  // 快速问答：正在输出
  | "done"
  | "stopped"
  | "error";

export interface UserMessage { id: string; role: "user"; text: string }

export interface AssistantMessage {
  id: string;
  role: "assistant";
  mode: Mode;
  question: string;
  text: string;
  status: AssistantStatus;
  claims?: Claim[];
  trust?: number;
  coverage?: number;
  evidence?: Record<string, Evidence>;
  plan?: string[];
  threadId?: string;
  trace?: TraceEvent[];
  error?: string;
  errorStatus?: number;
  feedback?: "up" | "down";
}

export type Message = UserMessage | AssistantMessage;

export interface Session {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: Message[];
}
