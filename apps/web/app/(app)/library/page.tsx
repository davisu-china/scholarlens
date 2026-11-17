"use client";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { FileText, Loader2, MessageSquare, Search, UploadCloud } from "lucide-react";
import { useCollections, usePapers } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { useApp } from "@/store/app";
import { Button } from "@/components/ui/button";

export default function LibraryPage() {
  const router = useRouter();
  const { data: papers, isLoading, isError, refetch } = usePapers();
  const { data: cols } = useCollections();
  const { panel, setPanel, setUploadOpen, setCollection, newSession } = useApp();
  const [active, setActive] = useState<string | null>(null);
  const [kw, setKw] = useState("");

  const list = useMemo(() => {
    const k = kw.trim().toLowerCase();
    return (papers ?? [])
      .filter((p) => (active ? p.collection === active : true))
      .filter((p) => (k ? (p.title || p.paper_id).toLowerCase().includes(k) : true));
  }, [papers, active, kw]);

  const ask = () => { setCollection(active); newSession(); router.push("/"); };
  const total = papers?.length ?? 0;
  const tab = "h-8 shrink-0 rounded-full px-3 text-[13px] transition-colors";

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <header className="shrink-0 px-5 pt-14 sm:px-8 lg:pt-8">
        <div className="mx-auto flex w-full max-w-[980px] flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-[26px] font-semibold tracking-tight">文献库</h1>
            <p className="mt-1 text-sm text-fg2">{total > 0 ? `共 ${total} 篇论文。问答和深度研究只依据这里的内容。` : "导入论文后，就可以在它们上面提问和做研究。"}</p>
          </div>
          <div className="flex gap-2">
            {total > 0 && <Button onClick={ask}><MessageSquare size={15} /> {active ? `就「${active}」提问` : "提问"}</Button>}
            <Button variant="primary" onClick={() => setUploadOpen(true)}><UploadCloud size={15} /> 导入论文</Button>
          </div>
        </div>

        {total > 0 && (
          <div className="mx-auto mt-6 flex w-full max-w-[980px] items-center gap-3">
            <div className="flex min-w-0 flex-1 gap-1 overflow-x-auto" role="tablist" aria-label="文献库分组">
              <button type="button" role="tab" aria-selected={active === null} onClick={() => setActive(null)}
                className={cn(tab, active === null ? "bg-fg text-bg" : "text-fg2 hover:bg-fg/5")}>全部 {total}</button>
              {(cols ?? []).map((c) => (
                <button key={c.name} type="button" role="tab" aria-selected={active === c.name} onClick={() => setActive(c.name)}
                  className={cn(tab, active === c.name ? "bg-fg text-bg" : "text-fg2 hover:bg-fg/5")}>{c.name} {c.count}</button>
              ))}
            </div>
            <label className="relative shrink-0">
              <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-fg3" />
              <input value={kw} onChange={(e) => setKw(e.target.value)} placeholder="搜索标题" aria-label="搜索标题"
                className="h-8 w-[140px] rounded-full sm:w-[200px] border bg-surface pl-8 pr-3 text-[13px] outline-none placeholder:text-fg3 focus:border-accent" />
            </label>
          </div>
        )}
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-10 pt-4 sm:px-8">
        <div className="mx-auto w-full max-w-[980px]">
          {isLoading ? (
            <div className="flex h-48 items-center justify-center text-fg3"><Loader2 size={18} className="animate-spin" /></div>
          ) : isError ? (
            <div className="rounded-2xl border p-8 text-center text-sm text-fg2">
              文献列表加载失败。<button type="button" onClick={() => refetch()} className="text-accent hover:underline">重试</button>
            </div>
          ) : total === 0 ? (
            <button type="button" onClick={() => setUploadOpen(true)}
              className="mt-4 flex w-full flex-col items-center rounded-3xl border-2 border-dashed bg-surface2 px-6 py-16 text-center transition-colors hover:border-accent/50 hover:bg-accent-soft/30">
              <span className="grid h-12 w-12 place-items-center rounded-full bg-accent-soft text-accent"><UploadCloud size={22} /></span>
              <span className="mt-4 text-[17px] font-semibold">导入第一批论文</span>
              <span className="mt-1 max-w-sm text-sm leading-relaxed text-fg2">上传 PDF，系统会解析正文、公式和表格。之后的每个回答都能定位到这些论文的具体页面。</span>
            </button>
          ) : list.length === 0 ? (
            <p className="py-16 text-center text-sm text-fg2">没有匹配的论文。</p>
          ) : (
            <ul className="divide-y overflow-hidden rounded-2xl border">
              {list.map((p) => {
                const open = panel?.kind === "paper" && panel.paperId === p.paper_id;
                return (
                  <li key={p.paper_id}>
                    <button type="button" onClick={() => setPanel({ kind: "paper", paperId: p.paper_id })}
                      className={cn("flex w-full items-center gap-3.5 px-4 py-3 text-left transition-colors", open ? "bg-accent-soft/60" : "hover:bg-surface2")}>
                      <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-fg/5 text-fg2"><FileText size={17} /></span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{p.title || p.paper_id}</span>
                        <span className="mt-0.5 block truncate text-xs text-fg3">
                          {[p.year, p.collection, `${p.n_chunks} 个片段`].filter(Boolean).join(" · ")}
                        </span>
                      </span>
                      <span className="shrink-0 text-xs text-fg3">{open ? "阅读中" : "阅读"}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
