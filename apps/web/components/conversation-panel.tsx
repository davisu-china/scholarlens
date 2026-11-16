"use client";
import { useState } from "react";
import { askQuestion } from "@/lib/api";

/** 中栏：对话 + 研究 Trace 时间线。PRD「问答 / 深度研究」。 */
export function ConversationPanel() {
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);

  async function onAsk(q: string) {
    setAnswer("");
    setLoading(true);
    try {
      for await (const ev of askQuestion(q)) {
        if (ev.event === "token") setAnswer((a) => a + ev.data);
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="flex flex-col">
      <div className="flex-1 overflow-y-auto p-6">
        {/* TODO: 渲染消息流 + Research Trace 时间线 + 引用角标 [n] */}
        <p className="whitespace-pre-wrap text-[15px] leading-7">{answer}</p>
      </div>
      <form
        className="border-t border-line p-4"
        onSubmit={(e) => {
          e.preventDefault();
          const input = (e.currentTarget.elements.namedItem("q") as HTMLInputElement);
          if (input.value.trim()) onAsk(input.value.trim());
        }}
      >
        <input
          name="q"
          disabled={loading}
          placeholder="提出一个研究问题…"
          className="w-full rounded-lg border border-line bg-surface px-4 py-3 text-sm outline-none focus:border-accent"
        />
      </form>
    </section>
  );
}
