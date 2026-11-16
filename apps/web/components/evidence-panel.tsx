"use client";
import { useSession } from "@/store/session";
import { Card, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/** 右栏：证据卡片 + PDF 原文占位。点击答案角标会高亮对应证据。 */
export function EvidencePanel() {
  const { evidence, selectedEid, selectEvidence } = useSession();
  const items = Object.entries(evidence);

  return (
    <aside className="flex flex-col gap-4 overflow-y-auto bg-surface/40 p-5">
      <h3 className="text-xs uppercase tracking-wide text-[#98a1b3]">Evidence</h3>

      {items.length === 0 && (
        <p className="text-sm text-[#98a1b3]">提问后，这里显示每条结论对应的证据与原文位置。</p>
      )}

      {items.map(([eid, ev]) => (
        <Card
          key={eid}
          className={cn("cursor-pointer transition", selectedEid === eid && "border-accent")}
          onClick={() => selectEvidence(eid)}
        >
          <CardBody>
            <div className="mb-1 flex items-center justify-between">
              <Badge tone="default">[{eid}]</Badge>
              <span className="text-xs text-[#6b7385]">
                {ev.provenance.paper_id} · p.{ev.provenance.bboxes?.[0]?.page ?? "?"}
              </span>
            </div>
            <p className="text-sm text-[#c7ccd8]">{ev.text}</p>
            {ev.section_path?.length > 0 && (
              <div className="mt-1 text-xs text-[#6b7385]">{ev.section_path.join(" / ")}</div>
            )}
          </CardBody>
        </Card>
      ))}

      {selectedEid && evidence[selectedEid] && (
        <div className="mt-2 rounded-lg border border-line p-3 text-xs text-[#98a1b3]">
          PDF 原文预览（接 react-pdf）：第 {evidence[selectedEid].provenance.bboxes?.[0]?.page ?? "?"} 页，
          叠加 bbox 高亮 — 此处为占位。
        </div>
      )}
    </aside>
  );
}
