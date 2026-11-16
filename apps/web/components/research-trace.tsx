"use client";
import type { TraceEvent } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const ICON: Record<string, string> = {
  plan: "✓", research: "✓", reflect: "◌", write: "✓", verify: "●",
};

/** 深度研究模式的过程时间线（PRD Research Trace）。 */
export function ResearchTrace({ steps }: { steps: TraceEvent[] }) {
  if (!steps.length) return null;
  return (
    <div className="mb-4 rounded-lg border border-line bg-surface/40 p-3">
      <div className="mb-2 text-xs uppercase tracking-wide text-[#98a1b3]">Research Trace</div>
      <ol className="space-y-1.5">
        {steps.map((s, i) => (
          <li key={i} className="flex items-start gap-2 text-sm">
            <span className="mt-0.5 text-accent">{ICON[s.kind] ?? "·"}</span>
            <span className="text-[#c7ccd8]">
              <Badge className="mr-2">{s.kind}</Badge>
              {String(s.data.detail ?? "")}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
