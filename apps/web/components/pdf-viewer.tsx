"use client";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { ChevronLeft, ChevronRight, FileWarning, Loader2, LocateFixed, Minus, Plus } from "lucide-react";
import { fetchPdfUrl } from "@/lib/api";
import type { BBox } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Tip } from "@/components/ui/tip";

// worker 由 scripts/copy-pdf-worker.mjs 拷到 public/，不依赖外部 CDN
pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";

const NORM = 1000; // 后端 bbox 归一化到 0–1000

/**
 * PDF 原文阅读 + 坐标高亮。
 * boxes：证据所在的段落（浅色）；focus：与论断最相近的那一句（深色）。
 */
export default function PdfViewer({
  paperId, targetPage, boxes = [], focus = [], className,
}: {
  paperId: string;
  targetPage?: number;
  boxes?: BBox[];
  focus?: BBox[];
  className?: string;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [numPages, setNumPages] = useState(0);
  const [page, setPage] = useState(targetPage ?? 1);
  const [zoom, setZoom] = useState(1);
  const [width, setWidth] = useState(0);
  const wrapRef = useRef<HTMLDivElement>(null);
  const markRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    let made: string | null = null;
    setUrl(null); setError(null); setNumPages(0);
    fetchPdfUrl(paperId)
      .then((u) => { made = u; if (alive) setUrl(u); else URL.revokeObjectURL(u); })
      .catch((e) => alive && setError(e?.message ?? "原文加载失败"));
    return () => { alive = false; if (made) URL.revokeObjectURL(made); };
  }, [paperId]);

  // 换了证据就跳到它所在的页
  const targetKey = `${paperId}:${targetPage}:${boxes[0]?.y0 ?? ""}:${focus[0]?.y0 ?? ""}`;
  useEffect(() => { if (targetPage) setPage(targetPage); }, [targetKey]); // eslint-disable-line react-hooks/exhaustive-deps

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.floor(e.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const scrollToMark = () => markRef.current?.scrollIntoView({ block: "center", behavior: "smooth" });
  const onPage = (list: BBox[]) => list.filter((b) => b.page === page);
  const pageBoxes = onPage(boxes);
  const pageFocus = onPage(focus);
  const hasMark = pageBoxes.length + pageFocus.length > 0;
  const pct = (b: BBox) => ({
    left: `${(b.x0 / NORM) * 100}%`, top: `${(b.y0 / NORM) * 100}%`,
    width: `${((b.x1 - b.x0) / NORM) * 100}%`, height: `${((b.y1 - b.y0) / NORM) * 100}%`,
  });
  const btn = "grid h-7 w-7 place-items-center rounded-full text-fg2 hover:bg-fg/5 hover:text-fg disabled:opacity-30 disabled:hover:bg-transparent";

  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div className="flex shrink-0 items-center gap-0.5 border-b px-2 py-1.5 text-xs text-fg2">
        <button type="button" className={btn} aria-label="上一页" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}><ChevronLeft size={15} /></button>
        <span className="min-w-[72px] text-center tabular-nums">第 {page} / {numPages || "–"} 页</span>
        <button type="button" className={btn} aria-label="下一页" disabled={!numPages || page >= numPages} onClick={() => setPage((p) => p + 1)}><ChevronRight size={15} /></button>
        {targetPage && (page !== targetPage || hasMark) && (
          <Tip label="回到引用位置">
            <button type="button" className={cn(btn, "ml-1 text-accent")} aria-label="回到引用位置"
              onClick={() => { if (page !== targetPage) setPage(targetPage); else scrollToMark(); }}>
              <LocateFixed size={14} />
            </button>
          </Tip>
        )}
        <span className="ml-auto" />
        <button type="button" className={btn} aria-label="缩小" disabled={zoom <= 0.6} onClick={() => setZoom((z) => Math.round((z - 0.2) * 10) / 10)}><Minus size={14} /></button>
        <span className="w-9 text-center tabular-nums">{Math.round(zoom * 100)}%</span>
        <button type="button" className={btn} aria-label="放大" disabled={zoom >= 2.4} onClick={() => setZoom((z) => Math.round((z + 0.2) * 10) / 10)}><Plus size={14} /></button>
      </div>

      <div ref={wrapRef} className="min-h-0 flex-1 overflow-auto bg-fg/[0.04]">
        {error ? (
          <div className="flex h-full min-h-[200px] flex-col items-center justify-center gap-2 p-6 text-center text-[13px] text-fg2">
            <FileWarning size={22} className="text-fg3" />
            {error}
          </div>
        ) : !url || !width ? (
          <Loading />
        ) : (
          <Document
            file={url}
            loading={<Loading />}
            error={<div className="p-6 text-center text-[13px] text-fg2">这个文件无法作为 PDF 打开</div>}
            onLoadSuccess={(d) => { setNumPages(d.numPages); setPage((p) => Math.min(Math.max(1, p), d.numPages)); }}
          >
            <div className="relative mx-auto my-3 w-fit bg-white shadow-card" style={{ width: Math.floor((width - 24) * zoom) }}>
              <Page
                pageNumber={Math.min(page, numPages || page)}
                width={Math.floor((width - 24) * zoom)}
                renderAnnotationLayer={false}
                renderTextLayer={false}
                loading={<div style={{ height: (width - 24) * zoom * 1.3 }} />}
                onRenderSuccess={() => requestAnimationFrame(scrollToMark)}
              />
              {pageBoxes.map((b, i) => (
                <div key={`b${i}`} ref={i === 0 && !pageFocus.length ? markRef : undefined}
                  className="pointer-events-none absolute rounded-[3px] bg-mark/25 ring-1 ring-mark/70 mix-blend-multiply" style={pct(b)} />
              ))}
              {pageFocus.map((b, i) => (
                <div key={`f${i}`} ref={i === 0 ? markRef : undefined}
                  className="pointer-events-none absolute rounded-[3px] bg-mark/45 ring-2 ring-mark mix-blend-multiply" style={pct(b)} />
              ))}
            </div>
          </Document>
        )}
      </div>
    </div>
  );
}

function Loading() {
  return (
    <div className="flex h-full min-h-[200px] items-center justify-center gap-2 text-[13px] text-fg3">
      <Loader2 size={15} className="animate-spin" /> 正在加载原文…
    </div>
  );
}
