"use client";

/** 右栏：证据面板 + PDF 原文（PDF.js + bbox 高亮）。PRD「PDF 阅读器」。 */
export function EvidencePanel() {
  return (
    <aside className="flex flex-col gap-4 overflow-y-auto bg-surface/40 p-5">
      <h3 className="text-xs uppercase tracking-wide text-[#98a1b3]">Evidence</h3>
      {/* TODO: 命中证据卡片（hover 显示原文片段）；点击角标 → 下方 PDF 跳页高亮 */}
      <div className="rounded-lg border border-line p-3 text-sm text-[#98a1b3]">
        选中答案里的引用角标后，这里显示对应证据与 PDF 原文。
      </div>
      {/* TODO: <PdfViewer> react-pdf 渲染 + 叠加 bbox 高亮层 */}
    </aside>
  );
}
