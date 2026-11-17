"use client";
import { useEffect, useRef } from "react";
import * as Menu from "@radix-ui/react-dropdown-menu";
import { ArrowUp, Check, ChevronDown, FolderOpen, Lock, Sparkles, Square, Telescope, Zap } from "lucide-react";
import { useCollections, useModels } from "@/lib/hooks";
import type { Mode } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useApp } from "@/store/app";
import { Tip } from "@/components/ui/tip";

const menuCls = "z-50 min-w-[220px] max-w-[320px] rounded-xl border bg-surface p-1 shadow-pop animate-fade-up";
const itemCls = "flex cursor-default select-none items-start gap-2 rounded-lg px-2.5 py-2 text-[13px] outline-none data-[highlighted]:bg-fg/5 data-[disabled]:opacity-45";
const pillCls = "inline-flex h-8 max-w-[180px] shrink-0 items-center gap-1.5 rounded-full px-2.5 text-[13px] text-fg2 transition-colors hover:bg-fg/5 hover:text-fg data-[state=open]:bg-fg/5";

export function Composer({
  value, onChange, onSend, busy, blocked, onStop, onUpgrade, autoFocus,
}: {
  value: string;
  onChange: (v: string) => void;
  onSend: (q: string) => void;
  busy: boolean;
  /** 有一份研究计划在等确认：暂时不能发新问题 */
  blocked?: boolean;
  onStop: () => void;
  onUpgrade: () => void;
  autoFocus?: boolean;
}) {
  const mode = useApp((s) => s.mode);
  const setMode = useApp((s) => s.setMode);
  const ref = useRef<HTMLTextAreaElement>(null);
  const canSend = value.trim().length > 0 && !busy && !blocked;

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 220) + "px";
  }, [value]);

  const submit = () => {
    if (!canSend) return;
    onSend(value.trim());
    onChange("");
  };

  return (
    <div className="rounded-[26px] border bg-surface shadow-card transition-shadow focus-within:border-accent/50 focus-within:shadow-[0_0_0_4px_rgb(var(--accent)/0.08)]">
      <textarea
        ref={ref}
        value={value}
        rows={1}
        autoFocus={autoFocus}
        aria-label="输入问题"
        placeholder={blocked ? "先确认或取消上面的研究计划" : mode === "qa" ? "就文献库里的论文提问" : "提出一个需要综合多篇论文的研究问题"}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); }
        }}
        className="block max-h-[220px] w-full resize-none bg-transparent px-5 pb-1 pt-4 text-[15px] leading-relaxed outline-none placeholder:text-fg3"
      />
      <div className="flex items-center gap-1 overflow-x-auto px-2.5 pb-2.5 pt-1 [scrollbar-width:none]">
        <ModeSwitch mode={mode} onChange={setMode} />
        <ScopePicker />
        <ModelPicker onUpgrade={onUpgrade} />
        <div className="ml-auto shrink-0 pl-1">
          {busy ? (
            <Tip label="停止">
              <button type="button" onClick={onStop} aria-label="停止生成" className="grid h-9 w-9 place-items-center rounded-full bg-fg text-bg transition-opacity hover:opacity-85">
                <Square size={12} fill="currentColor" />
              </button>
            </Tip>
          ) : (
            <button
              type="button"
              onClick={submit}
              disabled={!canSend}
              aria-label="发送"
              className="grid h-9 w-9 place-items-center rounded-full bg-accent text-white transition disabled:bg-fg/10 disabled:text-fg3"
            >
              <ArrowUp size={18} strokeWidth={2.4} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ModeSwitch({ mode, onChange }: { mode: Mode; onChange: (m: Mode) => void }) {
  const opts: { id: Mode; label: string; icon: React.ReactNode; tip: string }[] = [
    { id: "qa", label: "快速问答", icon: <Zap size={13} />, tip: "几秒内给出带引用的回答，适合查找具体结论" },
    { id: "research", label: "深度研究", icon: <Telescope size={13} />, tip: "先制定计划，多轮检索后写成综述，需要 1–3 分钟" },
  ];
  return (
    <div role="radiogroup" aria-label="回答方式" className="mr-1 inline-flex shrink-0 rounded-full bg-fg/5 p-0.5">
      {opts.map((o) => (
        <Tip key={o.id} label={o.tip}>
          <button
            type="button"
            role="radio"
            aria-checked={mode === o.id}
            onClick={() => onChange(o.id)}
            className={cn(
              "inline-flex h-7 items-center gap-1 whitespace-nowrap rounded-full px-2.5 text-[13px] transition-all",
              mode === o.id ? "bg-surface font-medium text-fg shadow-card" : "text-fg2 hover:text-fg",
            )}
          >
            {o.icon}{o.label}
          </button>
        </Tip>
      ))}
    </div>
  );
}

function ScopePicker() {
  const { data: cols } = useCollections();
  const collection = useApp((s) => s.collection);
  const setCollection = useApp((s) => s.setCollection);
  // 选中的文献库已不存在时回到"全部"
  useEffect(() => {
    if (collection && cols && !cols.some((c) => c.name === collection)) setCollection(null);
  }, [cols, collection, setCollection]);
  const total = (cols ?? []).reduce((n, c) => n + c.count, 0);

  return (
    <Menu.Root>
      <Menu.Trigger className={pillCls} aria-label="提问范围">
        <FolderOpen size={14} className="shrink-0" />
        <span className="truncate">{collection ?? "全部文献"}</span>
        <ChevronDown size={13} className="shrink-0 opacity-60" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Content align="start" sideOffset={6} className={menuCls}>
          <Menu.Label className="px-2.5 pb-1 pt-1.5 text-xs text-fg3">在哪些文献里找答案</Menu.Label>
          <Menu.Item className={itemCls} onSelect={() => setCollection(null)}>
            <span className="flex-1">全部文献</span>
            <span className="text-fg3">{total}</span>
            {collection === null && <Check size={14} className="text-accent" />}
          </Menu.Item>
          {(cols ?? []).map((c) => (
            <Menu.Item key={c.name} className={itemCls} onSelect={() => setCollection(c.name)}>
              <span className="flex-1 truncate">{c.name}</span>
              <span className="text-fg3">{c.count}</span>
              {collection === c.name && <Check size={14} className="text-accent" />}
            </Menu.Item>
          ))}
          {cols && cols.length === 0 && <div className="px-2.5 py-2 text-[13px] text-fg3">文献库还是空的</div>}
        </Menu.Content>
      </Menu.Portal>
    </Menu.Root>
  );
}

function ModelPicker({ onUpgrade }: { onUpgrade: () => void }) {
  const { data } = useModels();
  const model = useApp((s) => s.model);
  const setModel = useApp((s) => s.setModel);
  const models = data?.models ?? [];
  // 没选过、或选中的模型已不可用时，用服务端给的默认值
  useEffect(() => {
    if (!data) return;
    const cur = data.models.find((m) => m.id === model);
    if (!cur || cur.locked) setModel(data.default);
  }, [data, model, setModel]);
  if (!models.length) return null;
  const current = models.find((m) => m.id === model);

  return (
    <Menu.Root>
      <Menu.Trigger className={pillCls} aria-label="选择模型">
        <Sparkles size={14} className="shrink-0" />
        <span className="truncate">{current?.label ?? "模型"}</span>
        <ChevronDown size={13} className="shrink-0 opacity-60" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Content align="start" sideOffset={6} className={menuCls}>
          <Menu.Label className="px-2.5 pb-1 pt-1.5 text-xs text-fg3">模型</Menu.Label>
          {models.map((m) => (
            <Menu.Item key={m.id} className={itemCls} onSelect={() => (m.locked ? onUpgrade() : setModel(m.id))}>
              <span className="min-w-0 flex-1">
                <span className={cn("block", m.locked && "text-fg2")}>{m.label}</span>
                {m.description && <span className="mt-0.5 block text-xs leading-snug text-fg3">{m.description}</span>}
              </span>
              {m.locked ? (
                <span className="mt-0.5 inline-flex shrink-0 items-center gap-1 text-xs text-fg3"><Lock size={11} /> 升级解锁</span>
              ) : (
                model === m.id && <Check size={14} className="mt-0.5 shrink-0 text-accent" />
              )}
            </Menu.Item>
          ))}
        </Menu.Content>
      </Menu.Portal>
    </Menu.Root>
  );
}
