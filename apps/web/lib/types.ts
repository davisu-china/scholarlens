// 与后端 API 对齐的类型（见 core/domain.py、apps/api/routers）。

export interface Provenance {
  paper_id: string;
  block_id: string;
  bboxes: { page: number; x0: number; y0: number; x1: number; y1: number }[];
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
  evidence: Record<string, Evidence>;
}

export interface TraceEvent {
  kind: string; // plan / research / reflect / write / verify / answer
  detail?: string;
  data: Record<string, unknown>;
}

export interface ResearchAnswer {
  answer: string;
  trust: number;
  claims: Claim[];
  coverage: number;
}
