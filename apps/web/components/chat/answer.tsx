"use client";
import { memo, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { firstPage, linkCitations, parseCiteHref } from "@/lib/cite";
import { usePaperTitles } from "@/lib/hooks";
import type { Claim, Evidence } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Tip } from "@/components/ui/tip";

/** 渲染回答正文：Markdown + 公式 + 可点击的引用角标。 */
export const Answer = memo(function Answer({
  text, claims, evidence, streaming, activeEid, onCite,
}: {
  text: string;
  claims?: Claim[];
  evidence?: Record<string, Evidence>;
  streaming?: boolean;
  activeEid?: string | null;
  onCite: (eid: string) => void;
}) {
  const titleOf = usePaperTitles();
  const md = useMemo(() => linkCitations(text, evidence, claims), [text, evidence, claims]);

  return (
    <div className={cn("prose-answer", streaming && "is-streaming")}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          a({ href, children }) {
            const cite = parseCiteHref(href);
            if (!cite) {
              return <a href={href} target="_blank" rel="noreferrer" className="text-accent underline-offset-2 hover:underline">{children}</a>;
            }
            const ev = evidence?.[cite.eid];
            const page = firstPage(ev);
            const chip = (
              <button
                type="button"
                onClick={() => onCite(cite.eid)}
                aria-label={`查看第 ${String(children)} 条证据`}
                className={cn(
                  "relative -top-[1px] mx-[1.5px] inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-md px-1 align-middle font-mono text-[11px] font-semibold leading-none transition-colors",
                  cite.ok
                    ? "bg-accent-soft text-accent hover:bg-accent hover:text-white"
                    : "bg-warn/15 text-warn underline decoration-dotted underline-offset-2 hover:bg-warn hover:text-white",
                  activeEid === cite.eid && (cite.ok ? "bg-accent text-white" : "bg-warn text-white"),
                )}
              >
                {children}
              </button>
            );
            if (!ev) return <span className="whitespace-nowrap">{chip}{cite.punct}</span>;
            return (
              <span className="whitespace-nowrap">
              <Tip
                label={
                  <span className="block max-w-[280px]">
                    {!cite.ok && <span className="mb-1 block font-medium">这句没有通过引用校验，建议核对原文</span>}
                    <span className="block opacity-80">{titleOf(ev.provenance.paper_id)}{page ? ` · 第 ${page} 页` : ""}</span>
                    <span className="mt-1 block">{ev.text.length > 120 ? ev.text.slice(0, 120) + "…" : ev.text}</span>
                  </span>
                }
              >
                {chip}
              </Tip>
              {cite.punct}
              </span>
            );
          },
          table({ children }) {
            return <div className="table-wrap"><table>{children}</table></div>;
          },
        }}
      >
        {md}
      </ReactMarkdown>
    </div>
  );
});
