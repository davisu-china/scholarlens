"use client";
import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { fetchPdfUrl } from "@/lib/api";
import type { Provenance } from "@/lib/types";

// react-pdf 需要 worker；用 CDN 版，避免打包配置
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

const WIDTH = 360;        // 渲染页宽（px）
const NORM = 1000;        // MinerU bbox 归一化基准

/** PDF 原文预览 + bbox 高亮（溯源）。provenance 的坐标已归一化到 0–1000。 */
export function PdfViewer({ paperId, provenance }: { paperId: string; provenance: Provenance }) {
  const [url, setUrl] = useState<string | null>(null);
  const [pageSize, setPageSize] = useState<{ w: number; h: number } | null>(null);
  const box = provenance.bboxes?.[0];
  const page = box?.page ?? 1;

  useEffect(() => {
    let revoked: string | null = null;
    fetchPdfUrl(paperId).then((u) => { revoked = u; setUrl(u); }).catch(() => setUrl(null));
    return () => { if (revoked) URL.revokeObjectURL(revoked); };
  }, [paperId]);

  if (!url) return <div className="p-3 text-xs text-[#98a1b3]">加载原文…</div>;

  // 把归一化 bbox 换算成渲染像素（按实际页高缩放）
  const scale = pageSize ? pageSize.w / NORM : WIDTH / NORM;
  const hi = box && pageSize ? {
    left: box.x0 * scale, top: box.y0 * (pageSize.h / NORM),
    width: (box.x1 - box.x0) * scale, height: (box.y1 - box.y0) * (pageSize.h / NORM),
  } : null;

  return (
    <div className="relative overflow-hidden rounded-lg border border-line">
      <Document file={url} loading={<div className="p-3 text-xs text-[#98a1b3]">解析 PDF…</div>}>
        <Page
          pageNumber={page}
          width={WIDTH}
          renderTextLayer={false}
          renderAnnotationLayer={false}
          onRenderSuccess={(pg) => setPageSize({ w: WIDTH, h: (pg.height / pg.width) * WIDTH })}
        />
      </Document>
      {hi && (
        <div className="pointer-events-none absolute border-2 border-accent bg-accent/20"
             style={{ left: hi.left, top: hi.top, width: hi.width, height: hi.height }} />
      )}
      <div className="border-t border-line px-2 py-1 text-xs text-[#6b7385]">
        {provenance.paper_id} · 第 {page} 页
      </div>
    </div>
  );
}
