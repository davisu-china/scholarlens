"use client";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { ArrowDown, BookOpen, UploadCloud } from "lucide-react";
import { stopMessage, useChat } from "@/lib/chat";
import { usePapers } from "@/lib/hooks";
import type { AssistantMessage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { useApp, useCurrentSession } from "@/store/app";
import { Composer } from "@/components/chat/composer";
import { AssistantBlock, UserBubble } from "@/components/chat/message";
import { Button } from "@/components/ui/button";

const BUSY = ["planning", "running", "streaming"];

const EXAMPLES: Record<"qa" | "research", string[]> = {
  qa: ["这些论文各自要解决什么问题？", "哪些论文报告了实验结果？用的什么数据集？", "作者提到了哪些局限？"],
  research: ["梳理库里这些方法的演进脉络", "对比各方法的核心思路、实验结果和代价", "这个方向还有哪些没有解决的问题？"],
};

export default function ChatPage() {
  const session = useCurrentSession();
  const mode = useApp((s) => s.mode);
  const setPlansOpen = useApp((s) => s.setPlansOpen);
  const setUploadOpen = useApp((s) => s.setUploadOpen);
  const sidebarOpen = useApp((s) => s.sidebarOpen);
  const { send } = useChat();
  const { data: papers } = usePapers();
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const [atBottom, setAtBottom] = useState(true);

  const messages = session?.messages ?? [];
  const busyMsg = [...messages].reverse().find((m): m is AssistantMessage => m.role === "assistant" && BUSY.includes(m.status));
  // 等待确认计划时也不允许再发新问题，避免同一会话里并行两条
  const waitingPlan = messages.some((m) => m.role === "assistant" && m.status === "plan");
  const last = messages[messages.length - 1];
  const lastLen = last?.role === "assistant" ? last.text.length + (last.status?.length ?? 0) : 0;

  // 新内容到达时，如果用户本来就在底部，就跟着滚
  useEffect(() => {
    const el = scrollRef.current;
    if (el && atBottom) el.scrollTop = el.scrollHeight;
  }, [messages.length, lastLen]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    const el = scrollRef.current;
    if (el) { el.scrollTop = el.scrollHeight; setAtBottom(true); }
  }, [session?.id]);

  const onSend = (q: string) => { setAtBottom(true); send(q); };
  const composer = (
    <Composer
      value={draft} onChange={setDraft} onSend={onSend}
      busy={!!busyMsg}
      blocked={waitingPlan}
      onStop={() => busyMsg && session && stopMessage(session.id, busyMsg.id)}
      onUpgrade={() => setPlansOpen(true)}
      autoFocus
    />
  );

  if (!session || messages.length === 0) {
    const empty = papers && papers.length === 0;
    return (
      <div className="flex flex-1 flex-col items-center justify-center overflow-y-auto px-6 pb-[12vh] pt-16">
        <div className="w-full max-w-[720px]">
          <h1 className="text-center text-[30px] font-semibold tracking-tight">想弄清什么？</h1>
          <p className="mt-2 text-center text-[15px] text-fg2">在你的文献库里找答案，每个结论都能点回原文的具体位置。</p>
          <div className="mt-8">{composer}</div>

          {empty ? (
            <div className="mt-5 flex items-center gap-3 rounded-2xl border bg-surface2 px-4 py-3.5">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-accent-soft text-accent"><BookOpen size={17} /></span>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium">文献库还是空的</div>
                <div className="text-[13px] text-fg2">先导入几篇论文，回答才有依据。</div>
              </div>
              <Button variant="primary" size="sm" onClick={() => setUploadOpen(true)}><UploadCloud size={14} /> 导入论文</Button>
            </div>
          ) : (
            <div className="mt-5 flex flex-wrap justify-center gap-2">
              {EXAMPLES[mode].map((q) => (
                <button key={q} type="button" onClick={() => setDraft(q)}
                  className="rounded-full border bg-surface px-3.5 py-1.5 text-[13px] text-fg2 transition-colors hover:border-accent/40 hover:bg-accent-soft/50 hover:text-fg">
                  {q}
                </button>
              ))}
            </div>
          )}
          {papers && papers.length > 0 && (
            <p className="mt-6 text-center text-xs text-fg3">
              当前文献库共 {papers.length} 篇 · <Link href="/library" className="hover:text-accent hover:underline">管理文献</Link>
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <>
      <header className={cn("flex h-14 shrink-0 items-center border-b px-6", !sidebarOpen && "pl-14")}>
        <h1 className="mx-auto w-full max-w-[760px] truncate text-[15px] font-semibold">{session.title}</h1>
      </header>
      <div
        ref={scrollRef}
        onScroll={(e) => {
          const el = e.currentTarget;
          setAtBottom(el.scrollHeight - el.scrollTop - el.clientHeight < 80);
        }}
        className="min-h-0 flex-1 overflow-y-auto"
      >
        <div className="mx-auto w-full max-w-[760px] space-y-7 px-6 pb-10 pt-8" aria-live="polite">
          {messages.map((m) =>
            m.role === "user" ? <UserBubble key={m.id} text={m.text} />
              : <AssistantBlock key={m.id} sessionId={session.id} m={m} onUpgrade={() => setPlansOpen(true)} />,
          )}
        </div>
      </div>
      <div className="relative shrink-0 px-6 pb-4">
        {!atBottom && (
          <button type="button" aria-label="回到底部"
            onClick={() => scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })}
            className="absolute -top-11 left-1/2 grid h-8 w-8 -translate-x-1/2 place-items-center rounded-full border bg-surface text-fg2 shadow-card hover:text-fg">
            <ArrowDown size={15} />
          </button>
        )}
        <div className="mx-auto w-full max-w-[760px]">
          {composer}
          <p className="mt-2 text-center text-xs text-fg3">回答只依据你文献库里的论文。AI 可能出错，重要结论请点开引用核对原文。</p>
        </div>
      </div>
    </>
  );
}
