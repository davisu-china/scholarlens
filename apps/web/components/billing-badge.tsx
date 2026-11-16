"use client";
import { useEffect, useState } from "react";
import { fetchBilling, upgradePlan } from "@/lib/api";
import { Badge } from "@/components/ui/badge";

type Overview = Awaited<ReturnType<typeof fetchBilling>>;

/** 套餐与用量徽标：当前套餐、配额剩余、累计成本；付费升级走支付流程。 */
export function BillingBadge() {
  const [ov, setOv] = useState<Overview | null>(null);
  const [busy, setBusy] = useState(false);

  const load = () => fetchBilling().then(setOv);
  useEffect(() => { load(); }, []);

  if (!ov) return null;
  const label: Record<string, string> = { query: "问答", research: "深度研究", ingest_pages: "入库页数" };

  async function upgrade() {
    setBusy(true);
    try { await upgradePlan("pro"); await load(); } finally { setBusy(false); }
  }

  return (
    <section className="mt-auto border-t border-line pt-3 text-xs">
      <div className="mb-2 flex items-center justify-between">
        <Badge tone={ov.plan.id === "free" ? "default" : "ok"}>{ov.plan.name}</Badge>
        {ov.plan.id === "free" ? (
          <button onClick={upgrade} disabled={busy}
            className="text-accent underline hover:opacity-80 disabled:opacity-50">
            {busy ? "支付中…" : "升级 Pro ¥99/月"}
          </button>
        ) : (
          <span className="text-[#6b7385]">¥{ov.plan.price_cny_per_month}/月</span>
        )}
      </div>
      <ul className="space-y-1 text-[#98a1b3]">
        {ov.quotas.filter((q) => q.window === "day" || q.action === "ingest_pages").map((q) => (
          <li key={q.action + q.window} className="flex justify-between">
            <span>{label[q.action] ?? q.action}</span>
            <span className="tabular-nums">{q.used}/{q.limit}</span>
          </li>
        ))}
        <li className="flex justify-between border-t border-line pt-1 text-[#6b7385]">
          <span>累计成本</span><span className="tabular-nums">¥{ov.usage.cost_cny.toFixed(4)}</span>
        </li>
      </ul>
    </section>
  );
}
