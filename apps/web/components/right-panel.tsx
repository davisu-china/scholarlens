"use client";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, FileText, X } from "lucide-react";
import { citeOrder, firstPage } from "@/lib/cite";
import { usePapers, usePaperTitles } from "@/lib/hooks";
import type { AssistantMessage, Evidence } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useApp } from "@/store/app";
import { Badge } from "@/components/ui/badge";

const PdfViewer = dynamic(() => import("@/components/pdf-viewer"), { ssr: false });
const CitationGraph = dynamic(() => import("@/components/citation-graph"), { ssr: false });

const iconBtn = "grid h-8 w-8 shrink-0 place-items-center rounded-full text-fg2 hover:bg-fg/5 hover:text-fg disabled:opacity-30 disabled:hover:bg-transparent";

/** 右侧面板：回答的证据与原文对照，或单篇论文阅读。 */
export function RightPanel() {
  const panel = useApp((s) => s.panel);
  const setPanel = useApp((s) => s.setPanel);
  useEffect(() => {
    if (!panel) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape" && !document.querySelector("[role=dialog]")) setPanel(null); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [panel, setPanel]);
  if (!panel) return null;
  return (
    <aside
      aria-label={panel.kind === "evidence" ? "证据与原文" : "论文阅读"}
      className="fixed inset-y-0 right-0 z-30 flex w-full animate-slide-in flex-col border-l bg-surface shadow-pop sm:w-[min(560px,92vw)] xl:static xl:z-auto xl:w-[min(42vw,580px)] xl:shrink-0 xl:shadow-none"
    >
      {panel.kind === "evidence" ? <EvidenceView key={panel.messageId} /> : <PaperView key={panel.paperId} paperId={panel.paperId} />}
    </aside>
  );
}

function EvidenceView() {
  const panel = useApp((s) => s.panel);
  const setPanel = useApp((s) => s.setPanel);
  const sessions = useApp((s) => s.sessions);
  const titleOf = usePaperTitles();
  const topRef = useRef<HTMLDivElement>(null);
  const p = panel?.kind === "evidence" ? panel : null;

  const msg = useMemo(() => {
    const s = sessions.find((x) => x.id === p?.sessionId);
    return s?.messages.find((m) => m.id === p?.messageId && m.role === "assistant") as AssistantMessage | undefined;
  }, [sessions, p?.sessionId, p?.messageId]);

  const items = useMemo(() => {
    if (!msg) return [] as { eid: string; n: number; ev: Evidence }[];
    return [...citeOrder(msg.text, msg.evidence)]
      .map(([eid, n]) => ({ eid, n, ev: msg.evidence?.[eid] }))
      .filter((x): x is { eid: string; n: number; ev: Evidence } => !!x.ev);
  }, [msg]);

  if (!p || !msg) return <Header title="证据" onClose={() => setPanel(null)} />;
  const idx = items.findIndex((x) => x.eid === p.eid);
  const cur = idx >= 0 ? items[idx] : null;
  const go = (eid: string | null) => { setPanel({ ...p, eid }); topRef.current?.scrollTo({ top: 0 }); };
  const failed = new Set((msg.claims ?? []).filter((c) => !c.supported).flatMap((c) => c.eids));
  // 与这条证据最相近的那句话的精确位置（由引用校验给出）
  const focus = cur ? (msg.claims ?? []).filter((c) => c.best_eid === cur.eid && c.span).flatMap((c) => c.span!.bboxes) : [];

  return (
    <>
      <Header
        title={cur ? `证据 ${cur.n}` : `全部证据 · ${items.length} 条`}
        onClose={() => setPanel(null)}
        left={cur && (
          <button type="button" className={iconBtn} aria-label="返回证据列表" onClick={() => go(null)}><ChevronLeft size={17} /></button>
        )}
        right={cur && items.length > 1 && (
          <div className="flex items-center text-xs text-fg3">
            <button type="button" className={iconBtn} aria-label="上一条证据" disabled={idx <= 0} onClick={() => go(items[idx - 1].eid)}><ChevronLeft size={16} /></button>
            <span className="tabular-nums">{idx + 1} / {items.length}</span>
            <button type="button" className={iconBtn} aria-label="下一条证据" disabled={idx >= items.length - 1} onClick={() => go(items[idx + 1].eid)}><ChevronRight size={16} /></button>
          </div>
        )}
      />
      {cur ? (
        <div className="flex min-h-0 flex-1 flex-col">
          <div className="max-h-[38%] shrink-0 overflow-y-auto border-b px-5 py-4">
            <div className="text-[13px] font-medium leading-snug">{titleOf(cur.ev.provenance.paper_id)}</div>
            <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-fg3">
              {firstPage(cur.ev) && <span>第 {firstPage(cur.ev)} 页</span>}
              {cur.ev.section_path?.length > 0 && <span className="truncate">{cur.ev.section_path.join(" › ")}</span>}
              {failed.has(cur.eid) && <Badge tone="warn">引用它的句子未通过校验</Badge>}
            </div>
            <blockquote className="mt-3 border-l-2 border-mark pl-3 text-[13.5px] leading-relaxed text-fg2">{cur.ev.text}</blockquote>
          </div>
          {cur.ev.provenance.bboxes?.length ? (
            <PdfViewer
              className="flex-1"
              paperId={cur.ev.provenance.paper_id}
              targetPage={focus[0]?.page ?? firstPage(cur.ev)}
              boxes={cur.ev.provenance.bboxes}
              focus={focus}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center p-8 text-center text-[13px] text-fg2">这条证据没有原文位置信息，无法在 PDF 中定位。</div>
          )}
        </div>
      ) : (
        <div ref={topRef} className="min-h-0 flex-1 space-y-2 overflow-y-auto p-4">
          {items.length === 0 && <p className="p-4 text-center text-[13px] text-fg2">这条回答没有引用证据。</p>}
          {items.map(({ eid, n, ev }) => (
            <button
              key={eid}
              type="button"
              onClick={() => go(eid)}
              className="block w-full rounded-xl border bg-surface p-3.5 text-left transition-colors hover:border-accent/50 hover:bg-accent-soft/40"
            >
              <div className="flex items-start gap-2.5">
                <span className={cn("mt-0.5 grid h-[18px] min-w-[18px] place-items-center rounded-md px-1 font-mono text-[11px] font-semibold",
                  failed.has(eid) ? "bg-warn/15 text-warn" : "bg-accent-soft text-accent")}>{n}</span>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] font-medium">{titleOf(ev.provenance.paper_id)}</div>
                  <div className="mt-0.5 truncate text-xs text-fg3">
                    {firstPage(ev) ? `第 ${firstPage(ev)} 页` : "位置未知"}
                    {ev.section_path?.length ? ` · ${ev.section_path.join(" › ")}` : ""}
                  </div>
                  <p className="mt-1.5 line-clamp-3 text-[13px] leading-relaxed text-fg2">{ev.text}</p>
                </div>
              </div>
            </button>
          ))}
        </div>
      )}
    </>
  );
}

function PaperView({ paperId }: { paperId: string }) {
  const setPanel = useApp((s) => s.setPanel);
  const { data: papers } = usePapers();
  const paper = papers?.find((x) => x.paper_id === paperId);
  const [tab, setTab] = useState<"pdf" | "graph">("pdf");
  return (
    <>
      <Header title={paper?.title ?? paperId} onClose={() => setPanel(null)} left={<FileText size={16} className="ml-2 mr-1 shrink-0 text-fg3" />} />
      <div className="flex shrink-0 gap-5 border-b px-5 text-[13px]" role="tablist">
        {([["pdf", "原文"], ["graph", "引用关系"]] as const).map(([id, label]) => (
          <button key={id} type="button" role="tab" aria-selected={tab === id} onClick={() => setTab(id)}
            className={cn("-mb-px border-b-2 py-2.5 transition-colors", tab === id ? "border-accent font-medium text-fg" : "border-transparent text-fg2 hover:text-fg")}>
            {label}
          </button>
        ))}
        {paper && <span className="ml-auto self-center text-xs text-fg3">{paper.collection}{paper.year ? ` · ${paper.year}` : ""}</span>}
      </div>
      {tab === "pdf" ? <PdfViewer className="flex-1" paperId={paperId} /> : <div className="min-h-0 flex-1"><CitationGraph paperId={paperId} /></div>}
    </>
  );
}

function Header({ title, onClose, left, right }: { title: string; onClose: () => void; left?: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="flex h-14 shrink-0 items-center gap-1 border-b pl-2 pr-2">
      {left}
      <h2 className={cn("min-w-0 flex-1 truncate text-[15px] font-semibold", !left && "pl-3")}>{title}</h2>
      {right}
      <button type="button" className={iconBtn} aria-label="关闭面板" onClick={onClose}><X size={17} /></button>
    </div>
  );
}
