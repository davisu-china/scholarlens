"use client";
import { useEffect, useState } from "react";
import { Check, ChevronRight, Loader2 } from "lucide-react";
import type { TraceEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

const LABEL: Record<string, string> = {
  plan: "制定计划", research: "检索文献", reflect: "评估证据", write: "撰写综述", verify: "校验引用",
};

/** 研究进行中。后端在全部完成后才返回过程记录，所以这里只如实显示"正在做什么"和已用时间。 */
export function ResearchRunning({ plan }: { plan: string[] }) {
  const [sec, setSec] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setSec((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="animate-fade-up rounded-2xl border bg-surface p-5 shadow-card" role="status">
      <div className="flex items-center gap-2.5 text-[15px] font-semibold">
        <Loader2 size={16} className="animate-spin text-accent" />
        正在研究
        <span className="ml-auto font-mono text-xs font-normal tabular-nums text-fg3">
          {Math.floor(sec / 60)}:{String(sec % 60).padStart(2, "0")}
        </span>
      </div>
      <p className="mt-1.5 text-[13px] leading-relaxed text-fg2">
        按 {plan.length} 个子问题检索文献、评估证据是否充分、撰写综述，最后逐句校验引用。通常需要 1–3 分钟，请保持这个页面打开。
      </p>
      <ol className="mt-3 space-y-1 text-[13px] text-fg2">
        {plan.map((q, i) => (
          <li key={i} className="flex gap-2">
            <span className="w-4 shrink-0 text-right font-mono text-xs leading-[1.7] text-fg3">{i + 1}</span>
            <span>{q}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/** 研究完成后的过程记录，默认折叠。 */
export function ResearchTrace({ steps, plan }: { steps: TraceEvent[]; plan: string[] }) {
  const [open, setOpen] = useState(false);
  if (!steps.length) return null;
  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="inline-flex items-center gap-1 rounded-full py-1 pr-2 text-[13px] text-fg2 hover:text-fg"
      >
        <ChevronRight size={14} className={cn("transition-transform", open && "rotate-90")} />
        研究过程 · {steps.length} 步
      </button>
      {open && (
        <ol className="ml-[6px] mt-1 space-y-2 border-l pl-4">
          {steps.map((s, i) => {
            // 计划可能被用户改过，以最终确认的版本为准
            const subs = s.kind === "plan" ? plan : undefined;
            const missing = s.kind === "reflect" ? (s.data.missing as string[] | undefined) : undefined;
            return (
              <li key={i} className="relative text-[13px]">
                <span className="absolute -left-[23px] top-[3px] grid h-3.5 w-3.5 place-items-center rounded-full bg-ok/15 text-ok">
                  <Check size={9} strokeWidth={3} />
                </span>
                <span className="font-medium">{LABEL[s.kind] ?? s.kind}</span>
                <span className="ml-2 text-fg2">{s.kind === "plan" ? `按 ${plan.length} 个子问题研究` : s.detail}</span>
                {subs?.length ? (
                  <ul className="mt-1 space-y-0.5 text-fg2">{subs.map((q, k) => <li key={k}>· {q}</li>)}</ul>
                ) : null}
                {missing?.length ? (
                  <div className="mt-1 text-fg3">尚未覆盖：{missing.slice(0, 4).join("；")}{missing.length > 4 ? " 等" : ""}</div>
                ) : null}
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
