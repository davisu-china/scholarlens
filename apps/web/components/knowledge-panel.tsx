"use client";
import { useEffect, useState } from "react";
import { Library, MessageSquarePlus } from "lucide-react";
import { fetchCollections } from "@/lib/api";
import { BillingBadge } from "@/components/billing-badge";

/** 左栏：Collections（真实分组）+ Sessions。PRD「知识库管理」。 */
export function KnowledgePanel() {
  const [cols, setCols] = useState<{ name: string; count: number }[]>([]);
  useEffect(() => { fetchCollections().then(setCols).catch(() => setCols([])); }, []);

  return (
    <aside className="flex flex-col gap-6 overflow-y-auto bg-surface/40 p-5">
      <div className="flex items-center gap-2 font-bold">
        <span className="text-accent">◈</span> ScholarLens
      </div>

      <section>
        <h3 className="mb-2 flex items-center gap-1.5 text-xs uppercase tracking-wide text-[#98a1b3]">
          <Library size={13} /> Collections
        </h3>
        <ul className="space-y-1 text-sm text-[#c7ccd8]">
          {cols.length === 0 && <li className="px-2 py-1 text-[#6b7385]">暂无文献，先导入 PDF</li>}
          {cols.map((c) => (
            <li key={c.name} className="flex justify-between rounded px-2 py-1 hover:bg-white/5">
              <span>{c.name}</span><span className="text-[#6b7385]">{c.count}</span>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h3 className="mb-2 flex items-center gap-1.5 text-xs uppercase tracking-wide text-[#98a1b3]">
          <MessageSquarePlus size={13} /> Sessions
        </h3>
        <button className="w-full rounded border border-line px-2 py-1.5 text-left text-sm hover:bg-white/5">
          + 新研究
        </button>
      </section>

      <BillingBadge />
    </aside>
  );
}
