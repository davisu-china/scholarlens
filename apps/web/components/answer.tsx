"use client";
import type { Claim } from "@/lib/types";
import { useSession } from "@/store/session";
import { cn } from "@/lib/utils";

/** 渲染答案文本，把 [eid] 变成可点击角标；未被证据支撑的句子标红。 */
export function Answer({ text, claims }: { text: string; claims?: Claim[] }) {
  const selectEvidence = useSession((s) => s.selectEvidence);
  const supportByEid = new Map<string, boolean>();
  claims?.forEach((c) => c.best_eid && supportByEid.set(c.best_eid, c.supported));

  const parts = text.split(/(\[[a-zA-Z0-9_,\s-]+\])/g);
  return (
    <p className="whitespace-pre-wrap text-[15px] leading-7">
      {parts.map((part, i) => {
        const m = part.match(/^\[([a-zA-Z0-9_,\s-]+)\]$/);
        if (!m) return <span key={i}>{part}</span>;
        const eid = m[1].split(",")[0].trim();
        const supported = supportByEid.get(eid);
        return (
          <sup
            key={i}
            onClick={() => selectEvidence(eid)}
            className={cn(
              "mx-0.5 cursor-pointer rounded px-1 text-[11px]",
              supported === false ? "bg-red-500/20 text-red-300" : "bg-accent/20 text-accent",
            )}
            title={supported === false ? "未通过引用校验" : "查看证据"}
          >
            {eid}
          </sup>
        );
      })}
    </p>
  );
}
