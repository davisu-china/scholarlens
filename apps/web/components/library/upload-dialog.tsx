"use client";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, FileText, Loader2, UploadCloud, X } from "lucide-react";
import { describeError, uploadPaper } from "@/lib/api";
import { useCollections } from "@/lib/hooks";
import { cn, uid } from "@/lib/utils";
import { useApp } from "@/store/app";
import { Button } from "@/components/ui/button";
import { Dialog } from "@/components/ui/dialog";

type Item = { id: string; file: File; status: "queued" | "working" | "done" | "error"; note?: string };

const MAX_MB = 100;

export function UploadDialog() {
  const open = useApp((s) => s.uploadOpen);
  const setOpen = useApp((s) => s.setUploadOpen);
  const setPlansOpen = useApp((s) => s.setPlansOpen);
  const qc = useQueryClient();
  const { data: cols } = useCollections();
  const [items, setItems] = useState<Item[]>([]);
  const [collection, setCollection] = useState("");
  const [running, setRunning] = useState(false);
  const [over, setOver] = useState(false);
  const [quotaHit, setQuotaHit] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const patch = (id: string, p: Partial<Item>) => setItems((xs) => xs.map((x) => (x.id === id ? { ...x, ...p } : x)));

  function addFiles(list: FileList | File[]) {
    const next: Item[] = [];
    for (const f of Array.from(list)) {
      const pdf = f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf");
      const tooBig = f.size > MAX_MB * 1024 * 1024;
      next.push({
        id: uid(), file: f,
        status: pdf && !tooBig ? "queued" : "error",
        note: !pdf ? "只支持 PDF 文件" : tooBig ? `文件超过 ${MAX_MB} MB` : undefined,
      });
    }
    setItems((xs) => [...xs, ...next]);
  }

  async function start() {
    const target = collection.trim() || "默认";
    setRunning(true); setQuotaHit(false);
    const queue = items.filter((x) => x.status === "queued");
    for (const it of queue) {
      patch(it.id, { status: "working" });
      try {
        const p = await uploadPaper(it.file, target);
        patch(it.id, { status: "done", note: p.title });
        void qc.invalidateQueries({ queryKey: ["papers"] });
        void qc.invalidateQueries({ queryKey: ["collections"] });
      } catch (e) {
        const { message, status } = describeError(e);
        patch(it.id, { status: "error", note: message });
        if (status === 429) {
          // 额度用完后面的也不会成功，直接停下
          setQuotaHit(true);
          setItems((xs) => xs.map((x) => (x.status === "queued" ? { ...x, status: "error", note: "额度不足，未上传" } : x)));
          break;
        }
      }
    }
    void qc.invalidateQueries({ queryKey: ["billing"] });
    setRunning(false);
  }

  const queued = items.filter((x) => x.status === "queued").length;
  const done = items.filter((x) => x.status === "done").length;
  const close = (v: boolean) => {
    if (running) return; // 解析中不允许关掉，避免用户以为已取消
    setOpen(v);
    if (!v) { setItems([]); setQuotaHit(false); }
  };

  return (
    <Dialog open={open} onOpenChange={close} title="导入论文" description="上传 PDF 后会解析版面、公式和表格并建立索引，每篇通常需要一两分钟。">
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); if (!running) addFiles(e.dataTransfer.files); }}
        className={cn("rounded-2xl border-2 border-dashed px-6 py-7 text-center transition-colors", over ? "border-accent bg-accent-soft/60" : "border-line bg-surface2")}
      >
        <UploadCloud size={26} className="mx-auto text-fg3" />
        <p className="mt-2 text-sm">把 PDF 拖到这里，或</p>
        <Button size="sm" className="mt-2" disabled={running} onClick={() => inputRef.current?.click()}>选择文件</Button>
        <input ref={inputRef} type="file" accept="application/pdf,.pdf" multiple hidden
          onChange={(e) => { if (e.target.files) addFiles(e.target.files); e.target.value = ""; }} />
        <p className="mt-2 text-xs text-fg3">可一次选择多个，单个文件不超过 {MAX_MB} MB</p>
      </div>

      <label className="mt-4 block text-[13px] font-medium" htmlFor="upload-collection">放入文献库</label>
      <input
        id="upload-collection" list="upload-collections" value={collection} disabled={running}
        onChange={(e) => setCollection(e.target.value)}
        placeholder="选择已有文献库，或输入新名称（留空则放入「默认」）"
        className="mt-1.5 h-10 w-full rounded-xl border bg-surface px-3 text-sm outline-none placeholder:text-fg3 focus:border-accent"
      />
      <datalist id="upload-collections">{(cols ?? []).map((c) => <option key={c.name} value={c.name} />)}</datalist>

      {items.length > 0 && (
        <ul className="mt-4 max-h-[220px] space-y-1.5 overflow-y-auto">
          {items.map((it) => (
            <li key={it.id} className="flex items-center gap-2.5 rounded-xl border bg-surface px-3 py-2">
              {it.status === "working" ? <Loader2 size={16} className="shrink-0 animate-spin text-accent" />
                : it.status === "done" ? <CheckCircle2 size={16} className="shrink-0 text-ok" />
                : it.status === "error" ? <AlertCircle size={16} className="shrink-0 text-bad" />
                : <FileText size={16} className="shrink-0 text-fg3" />}
              <div className="min-w-0 flex-1">
                <div className="truncate text-[13px]">{it.file.name}</div>
                <div className={cn("truncate text-xs", it.status === "error" ? "text-bad" : "text-fg3")}>
                  {it.status === "working" ? "正在解析并建立索引…"
                    : it.status === "done" ? `已入库${it.note ? `：${it.note}` : ""}`
                    : it.status === "error" ? it.note
                    : `${(it.file.size / 1024 / 1024).toFixed(1)} MB · 等待上传`}
                </div>
              </div>
              {(it.status === "queued" || it.status === "error") && !running && (
                <button type="button" aria-label={`移除 ${it.file.name}`} onClick={() => setItems((xs) => xs.filter((x) => x.id !== it.id))}
                  className="rounded-full p-1.5 text-fg3 hover:bg-fg/5 hover:text-fg"><X size={14} /></button>
              )}
            </li>
          ))}
        </ul>
      )}

      {quotaHit && (
        <div className="mt-3 flex items-center justify-between gap-3 rounded-xl bg-warn/10 px-3 py-2 text-[13px] text-warn">
          本月的解析额度已用完。
          <Button size="sm" variant="primary" onClick={() => setPlansOpen(true)}>查看套餐</Button>
        </div>
      )}

      <div className="mt-5 flex items-center justify-end gap-2">
        {running && <span className="mr-auto text-xs text-fg3">解析期间请不要关闭这个窗口</span>}
        {!running && done > 0 && queued === 0 ? (
          <Button variant="primary" onClick={() => close(false)}>完成</Button>
        ) : (
          <>
            <Button variant="ghost" disabled={running} onClick={() => close(false)}>取消</Button>
            <Button variant="primary" disabled={running || queued === 0} onClick={start}>
              {running ? <><Loader2 size={14} className="animate-spin" /> 正在导入</> : queued > 0 ? `导入 ${queued} 篇` : "导入"}
            </Button>
          </>
        )}
      </div>
    </Dialog>
  );
}
