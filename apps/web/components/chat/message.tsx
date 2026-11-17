"use client";
import { useMemo, useState } from "react";
import { AlertCircle, Check, ChevronRight, Copy, Library, Loader2, RotateCcw, ShieldAlert, ShieldCheck, Square } from "lucide-react";
import { stopMessage, useChat } from "@/lib/chat";
import { citeOrder } from "@/lib/cite";
import type { AssistantMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useApp } from "@/store/app";
import { Answer } from "./answer";
import { PlanEditor } from "./plan-editor";
import { ResearchRunning, ResearchTrace } from "./research-progress";
import { Button } from "@/components/ui/button";
import { Tip } from "@/components/ui/tip";

export function UserBubble({ text }: { text: string }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-[20px] rounded-br-md bg-accent-soft px-4 py-2.5 text-[15px] leading-relaxed">
        {text}
      </div>
    </div>
  );
}

export function AssistantBlock({ sessionId, m, onUpgrade }: { sessionId: string; m: AssistantMessage; onUpgrade: () => void }) {
  const { confirmPlan, retry } = useChat();
  const panel = useApp((s) => s.panel);
  const setPanel = useApp((s) => s.setPanel);
  const activeEid = panel?.kind === "evidence" && panel.messageId === m.id ? panel.eid : null;
  const openEvidence = (eid: string | null) => setPanel({ kind: "evidence", sessionId, messageId: m.id, eid });

  if (m.status === "planning") {
    return (
      <div className="flex items-center gap-2 text-sm text-fg2" role="status">
        <Loader2 size={15} className="animate-spin text-accent" /> 正在拆解问题、制定研究计划…
        <button type="button" onClick={() => stopMessage(sessionId, m.id)} className="ml-1 text-fg3 underline-offset-2 hover:text-fg hover:underline">取消</button>
      </div>
    );
  }

  if (m.status === "plan" && m.threadId) {
    return (
      <PlanEditor
        initial={m.plan ?? []}
        onConfirm={(plan) => confirmPlan(sessionId, m.id, m.threadId!, plan)}
        onCancel={() => useApp.getState().patchMessage(sessionId, m.id, { status: "stopped" })}
      />
    );
  }

  if (m.status === "running") {
    return (
      <div>
        <ResearchRunning plan={m.plan ?? []} />
        <Button variant="ghost" size="sm" className="mt-2" onClick={() => stopMessage(sessionId, m.id)}>
          <Square size={12} fill="currentColor" /> 停止
        </Button>
      </div>
    );
  }

  if (m.status === "error") {
    const quota = m.errorStatus === 429 || m.errorStatus === 403;
    return (
      <div className="animate-fade-up rounded-2xl border border-bad/25 bg-bad/5 p-4" role="alert">
        <div className="flex gap-2.5">
          <AlertCircle size={17} className="mt-0.5 shrink-0 text-bad" />
          <div className="min-w-0">
            <div className="text-sm font-medium">{quota ? "额度或权限不足" : "这次没有成功"}</div>
            <p className="mt-0.5 break-words text-[13px] leading-relaxed text-fg2">{m.error}</p>
            <div className="mt-3 flex gap-2">
              {quota && <Button variant="primary" size="sm" onClick={onUpgrade}>查看套餐</Button>}
              <Button size="sm" onClick={() => retry(sessionId, m)}><RotateCcw size={13} /> 重试</Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const streaming = m.status === "streaming";
  return (
    <div className="animate-fade-up">
      {m.mode === "research" && m.trace && <ResearchTrace steps={m.trace} plan={m.plan ?? []} />}
      {m.text ? (
        <Answer text={m.text} claims={m.claims} evidence={m.evidence} streaming={streaming} activeEid={activeEid} onCite={openEvidence} />
      ) : streaming ? (
        <div className="flex items-center gap-2 text-sm text-fg2" role="status">
          <Loader2 size={15} className="animate-spin text-accent" /> 正在检索文献…
        </div>
      ) : (
        <p className="text-sm text-fg2">
          {m.status === "done" ? "文献库里没有找到足以回答这个问题的证据。可以换个问法，或先导入相关论文。" : "已停止，没有生成内容。"}
        </p>
      )}

      {streaming && m.text && (
        <p className="mt-3 text-xs text-fg3">生成完成后会逐句校验引用。</p>
      )}
      {m.status === "stopped" && m.text && <p className="mt-3 text-xs text-fg3">已停止生成，以上内容未经引用校验。</p>}
      {m.status === "done" && <Verification m={m} onOpen={() => openEvidence(null)} />}

      {!streaming && (
        <div className="mt-2 flex items-center gap-0.5 text-fg3">
          {m.text && <CopyButton text={m.text} />}
          <Tip label="重新生成">
            <button type="button" aria-label="重新生成" onClick={() => retry(sessionId, m)} className="rounded-full p-2 hover:bg-fg/5 hover:text-fg">
              <RotateCcw size={14} />
            </button>
          </Tip>
        </div>
      )}
    </div>
  );
}

function CopyButton({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <Tip label={done ? "已复制" : "复制"}>
      <button
        type="button"
        aria-label="复制回答"
        onClick={async () => {
          await navigator.clipboard?.writeText(text).catch(() => {});
          setDone(true);
          setTimeout(() => setDone(false), 1500);
        }}
        className="rounded-full p-2 hover:bg-fg/5 hover:text-fg"
      >
        {done ? <Check size={14} className="text-ok" /> : <Copy size={14} />}
      </button>
    </Tip>
  );
}

/** 回答下方的引用校验结果。 */
function Verification({ m, onOpen }: { m: AssistantMessage; onOpen: () => void }) {
  const [open, setOpen] = useState(false);
  const claims = m.claims ?? [];
  const failed = claims.filter((c) => !c.supported);
  const nEvidence = useMemo(() => citeOrder(m.text, m.evidence).size, [m.text, m.evidence]);
  if (!claims.length && !nEvidence) return null;
  const allOk = failed.length === 0;

  return (
    <div className="mt-4 rounded-xl border bg-surface2/70 px-3.5 py-2.5 text-[13px]">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
        {claims.length > 0 && (
          <span className={cn("inline-flex items-center gap-1.5 font-medium", allOk ? "text-ok" : "text-warn")}>
            {allOk ? <ShieldCheck size={15} /> : <ShieldAlert size={15} />}
            {allOk ? `${claims.length} 句均通过引用校验` : `${claims.length} 句中 ${failed.length} 句未通过引用校验`}
          </span>
        )}
        {m.mode === "research" && m.coverage !== undefined && (
          <Tip label="研究计划里需要回答的信息点中，在文献库里找到证据的比例。">
            <span className="cursor-help text-fg2">证据覆盖 {(m.coverage * 100).toFixed(0)}%</span>
          </Tip>
        )}
        {nEvidence > 0 && (
          <button type="button" onClick={onOpen} className="inline-flex items-center gap-1 text-fg2 hover:text-accent">
            <Library size={14} /> 查看 {nEvidence} 条证据
          </button>
        )}
        {!allOk && (
          <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open} className="ml-auto inline-flex items-center gap-0.5 text-fg2 hover:text-fg">
            {open ? "收起" : "查看未通过的句子"}
            <ChevronRight size={14} className={cn("transition-transform", open && "rotate-90")} />
          </button>
        )}
      </div>
      {open && (
        <ul className="mt-2.5 space-y-2 border-t pt-2.5">
          {failed.map((c, i) => (
            <li key={i} className="border-l-2 border-warn/60 pl-2.5 leading-relaxed text-fg2">
              {c.text}
              <span className="ml-1 text-fg3">{c.eids.length ? "· 引用的原文不足以支持这句话" : "· 没有标注来源"}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
