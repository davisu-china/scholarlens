"use client";
import { useRef, useState } from "react";
import { Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";

/** 深度研究的计划确认：用户可以增删改子问题，再开始执行。 */
export function PlanEditor({
  initial, onConfirm, onCancel,
}: {
  initial: string[];
  onConfirm: (plan: string[]) => void;
  onCancel: () => void;
}) {
  const [items, setItems] = useState(initial.length ? initial : [""]);
  const refs = useRef<(HTMLTextAreaElement | null)[]>([]);
  const valid = items.map((s) => s.trim()).filter(Boolean);

  const add = (at: number) => {
    setItems((xs) => [...xs.slice(0, at + 1), "", ...xs.slice(at + 1)]);
    requestAnimationFrame(() => refs.current[at + 1]?.focus());
  };

  return (
    <div className="animate-fade-up rounded-2xl border bg-surface p-5 shadow-card">
      <div className="text-[15px] font-semibold">研究计划</div>
      <p className="mt-1 text-[13px] leading-relaxed text-fg2">
        我会按下面的子问题分别检索和阅读，再汇总成综述。可以先修改、删除或补充，确认后开始。
      </p>
      <ol className="mt-4 space-y-2">
        {items.map((text, i) => (
          <li key={i} className="group flex items-start gap-2.5">
            <span className="mt-[9px] w-5 shrink-0 text-right font-mono text-xs text-fg3">{i + 1}</span>
            <textarea
              ref={(el) => { refs.current[i] = el; }}
              value={text}
              rows={1}
              placeholder="输入一个子问题"
              onChange={(e) => setItems((xs) => xs.map((x, k) => (k === i ? e.target.value : x)))}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); add(i); }
                if (e.key === "Backspace" && !text && items.length > 1) {
                  e.preventDefault();
                  setItems((xs) => xs.filter((_, k) => k !== i));
                  requestAnimationFrame(() => refs.current[Math.max(0, i - 1)]?.focus());
                }
              }}
              className="min-h-[36px] flex-1 resize-none rounded-xl border bg-surface2 px-3 py-[7px] text-sm leading-relaxed outline-none transition-colors [field-sizing:content] placeholder:text-fg3 focus:border-accent focus:bg-surface"
            />
            <button
              type="button"
              aria-label={`删除第 ${i + 1} 个子问题`}
              disabled={items.length <= 1}
              onClick={() => setItems((xs) => xs.filter((_, k) => k !== i))}
              className="mt-1 rounded-full p-1.5 text-fg3 opacity-0 transition hover:bg-fg/5 hover:text-bad focus-visible:opacity-100 disabled:hidden group-hover:opacity-100"
            >
              <X size={14} />
            </button>
          </li>
        ))}
      </ol>
      <button
        type="button"
        onClick={() => add(items.length - 1)}
        className="ml-[30px] mt-2 inline-flex items-center gap-1 rounded-full px-2 py-1 text-[13px] text-fg2 hover:bg-fg/5 hover:text-fg"
      >
        <Plus size={14} /> 添加子问题
      </button>
      <div className="mt-5 flex items-center gap-2">
        <Button variant="primary" disabled={!valid.length} onClick={() => onConfirm(valid)}>
          开始研究
        </Button>
        <Button variant="ghost" onClick={onCancel}>取消</Button>
        <span className="ml-auto text-xs text-fg3">通常需要 1–3 分钟</span>
      </div>
    </div>
  );
}
