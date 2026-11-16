"use client";
import { useSession } from "@/store/session";
import { Card, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PdfViewer } from "@/components/pdf-viewer";
import { cn } from "@/lib/utils";

/** 右栏：证据卡片 + PDF 原文高亮。点击答案角标或证据卡片即定位到原文坐标。 */
export function EvidencePanel() {
  const { evidence, selectedEid, selectEvidence } = useSession();
  const items = Object.entries(evidence);
  const sel = selectedEid ? evidence[selectedEid] : null;

  return (
    <aside className="flex flex-col gap-4 overflow-y-auto bg-surface/40 p-5">
      <h3 className="text-xs uppercase tracking-wide text-[#98a1b3]">Evidence</h3>

      {items.length === 0 && (
        <p className="text-sm text-[#98a1b3]">提问后，这里显示每条结论对应的证据与原文位置。</p>
      )}

      {items.map(([eid, ev]) => (
        <Card key={eid} className={cn("cursor-pointer transition", selectedEid === eid && "border-accent")}
              onClick={() => selectEvidence(eid)}>
          <CardBody>
            <div className="mb-1 flex items-center justify-between">
              <Badge>[{eid}]</Badge>
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

      {sel && sel.provenance.bboxes?.length > 0 && (
        <PdfViewer paperId={sel.provenance.paper_id} provenance={sel.provenance} />
      )}
    </aside>
  );
}
