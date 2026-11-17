"use client";
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Loader2 } from "lucide-react";
import { describeError, fetchPlans, upgradePlan } from "@/lib/api";
import { useBilling } from "@/lib/hooks";
import type { Plan } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useApp } from "@/store/app";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";

function features(p: Plan): string[] {
  const q = p.quotas;
  const lim = (a: string, unit: string) => {
    const x = q[a];
    if (!x || (x.per_day == null && x.per_month == null)) return "不限";
    return x.per_day != null ? `每天 ${x.per_day} ${unit}` : `每月 ${x.per_month} ${unit}`;
  };
  return [
    `快速问答：${lim("query", "次")}`,
    `深度研究：${lim("research", "次")}`,
    `文献解析：${lim("ingest_pages", "页")}`,
    p.allowed_models.includes("*") ? "可用全部模型" : "可用基础模型",
  ];
}

export function PlansDialog() {
  const open = useApp((s) => s.plansOpen);
  const setOpen = useApp((s) => s.setPlansOpen);
  const qc = useQueryClient();
  const { data: plans } = useQuery({ queryKey: ["plans"], queryFn: fetchPlans, enabled: open });
  const { data: billing } = useBilling();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const current = billing?.plan.id;

  async function upgrade(id: string) {
    setBusy(id); setError(null);
    try {
      await upgradePlan(id);
      await Promise.all([qc.invalidateQueries({ queryKey: ["billing"] }), qc.invalidateQueries({ queryKey: ["models"] })]);
    } catch (e) {
      setError(describeError(e).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen} title="套餐" description="额度按自然日和自然月重置。" className="w-[min(94vw,760px)]">
      {!plans ? (
        <div className="flex h-40 items-center justify-center text-fg3"><Loader2 size={18} className="animate-spin" /></div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-3">
          {plans.map((p) => {
            const isCurrent = p.id === current;
            const contact = p.id === "enterprise";
            return (
              <div key={p.id} className={cn("flex flex-col rounded-2xl border p-4", isCurrent && "border-accent ring-1 ring-accent")}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold">{p.name}</span>
                  {isCurrent && <span className="text-xs font-medium text-accent">当前套餐</span>}
                </div>
                <div className="mt-2 h-9">
                  {contact ? <span className="text-xl font-semibold">面议</span> : (
                    <><span className="text-[26px] font-semibold tracking-tight">¥{p.price_cny_per_month}</span><span className="text-xs text-fg3"> / 月</span></>
                  )}
                </div>
                <ul className="mt-3 flex-1 space-y-1.5 text-[13px] text-fg2">
                  {features(p).map((f) => (
                    <li key={f} className="flex gap-1.5"><Check size={14} className="mt-[3px] shrink-0 text-ok" />{f}</li>
                  ))}
                </ul>
                <div className="mt-4">
                  {isCurrent ? <Button className="w-full" disabled>使用中</Button>
                    : contact ? <Button className="w-full" disabled>请联系我们</Button>
                    : p.price_cny_per_month > 0 ? (
                      <Button variant="primary" className="w-full" disabled={!!busy} onClick={() => upgrade(p.id)}>
                        {busy === p.id ? <Loader2 size={14} className="animate-spin" /> : null} 升级到{p.name}
                      </Button>
                    ) : <Button className="w-full" disabled>到期后自动降级</Button>}
                </div>
              </div>
            );
          })}
        </div>
      )}
      {error && <p className="mt-3 text-[13px] text-bad" role="alert">{error}</p>}
      <p className="mt-4 text-xs leading-relaxed text-fg3">
        支付功能还在接入中：现在点击升级会直接生效，不会真实扣款。
      </p>
    </Dialog>
  );
}
