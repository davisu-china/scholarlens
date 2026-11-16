"use client";
import { Library, MessageSquarePlus } from "lucide-react";

/** 左栏：Collections + Sessions。PRD「知识库管理」。 */
export function KnowledgePanel() {
  return (
    <aside className="flex flex-col gap-6 overflow-y-auto bg-surface/40 p-5">
      <div className="flex items-center gap-2 font-bold">
        <span className="text-accent">◈</span> ScholarLens
      </div>

      <section>
        <h3 className="mb-2 flex items-center gap-1.5 text-xs uppercase tracking-wide text-[#98a1b3]">
          <Library size={13} /> Collections
        </h3>
        {/* TODO: GET /papers 按 collection 分组 */}
        <ul className="space-y-1 text-sm text-[#c7ccd8]">
          <li className="rounded px-2 py-1 hover:bg-white/5">Long-Context LLM · 128</li>
          <li className="rounded px-2 py-1 hover:bg-white/5">RAG Methods · 342</li>
          <li className="rounded px-2 py-1 hover:bg-white/5">Group Shared · 57</li>
        </ul>
      </section>

      <section>
        <h3 className="mb-2 flex items-center gap-1.5 text-xs uppercase tracking-wide text-[#98a1b3]">
          <MessageSquarePlus size={13} /> Sessions
        </h3>
        {/* TODO: 会话列表 + 新建 */}
        <button className="w-full rounded border border-line px-2 py-1.5 text-left text-sm hover:bg-white/5">
          + 新研究
        </button>
      </section>
    </aside>
  );
}
