"use client";
import { useEffect, useState } from "react";
import { fetchBilling, setPlan } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

type Overview = Awaited<ReturnType<typeof fetchBilling>>;

/** 套餐与用量徽标（商业化雏形）：显示当前套餐、配额剩余，可一键切换套餐演示。 */
export function BillingBadge() {
  const [ov, setOv] = useState<Overview | null>(null);

  const load = () => fetchBilling().then(setOv);
  useEffect(() => { load(); }, []);

  if (!ov) return null;
  const label: Record<string, string> = { query: "问答", research: "深度研究", ingest_pages: "入库页数" };

  async function toggle() {
    await setPlan(ov!.plan.id === "free" ? "pro" : "free");
    load();
  }

  return (
    <section className="mt-auto border-t border-line pt-3 text-xs">
      <div className="mb-2 flex items-center justify-between">
        <Badge tone={ov.plan.id === "free" ? "default" : "ok"}>{ov.plan.name}</Badge>
        <button onClick={toggle} className="text-[#98a1b3] underline hover:text-[#e7e9ef]">
          {ov.plan.id === "free" ? "升级 Pro" : "切回免费"}
        </button>
      </div>
      <ul className="space-y-1 text-[#98a1b3]">
        {ov.quotas.filter((q) => q.window === "day" || q.action === "ingest_pages").map((q) => (
          <li key={q.action + q.window} className="flex justify-between">
            <span>{label[q.action] ?? q.action}</span>
            <span className="tabular-nums">{q.used}/{q.limit}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
