"use client";
import { useState } from "react";
import { askQuestion, deepResearch } from "@/lib/api";
import type { TraceEvent } from "@/lib/types";
import { useSession } from "@/store/session";
import { Answer } from "@/components/answer";
import { ResearchTrace } from "@/components/research-trace";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function ConversationPanel() {
  const { messages, pushMessage, updateLast, setEvidence, deepMode, setDeepMode } = useSession();
  const [trace, setTrace] = useState<TraceEvent[]>([]);
  const [busy, setBusy] = useState(false);

  async function onSubmit(q: string) {
    setBusy(true);
    setTrace([]);
    pushMessage({ role: "user", text: q });
    pushMessage({ role: "assistant", text: "" });

    try {
      if (deepMode) {
        await deepResearch(q, {
          onTrace: (e) => setTrace((t) => [...t, e]),
          onAnswer: (a) => updateLast({ text: a.answer, claims: a.claims, trust: a.trust }),
        });
      } else {
        let acc = "";
        await askQuestion(q, {
          onToken: (t) => { acc += t; updateLast({ text: acc }); },
          onDone: (d) => { updateLast({ claims: d.claims, trust: d.trust }); setEvidence(d.evidence); },
        });
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col">
      <div className="flex items-center gap-2 border-b border-line px-6 py-3">
        <Button variant={deepMode ? "outline" : "default"} onClick={() => setDeepMode(false)}>快速问答</Button>
        <Button variant={deepMode ? "default" : "outline"} onClick={() => setDeepMode(true)}>深度研究</Button>
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto p-6">
        <ResearchTrace steps={trace} />
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="font-medium text-[#e7e9ef]">🙋 {m.text}</div>
          ) : (
            <div key={i} className="space-y-2">
              <Answer text={m.text} claims={m.claims} />
              {m.trust !== undefined && (
                <Badge tone={m.trust >= 0.9 ? "ok" : "default"}>可信度 {(m.trust * 100).toFixed(0)}%</Badge>
              )}
            </div>
          ),
        )}
      </div>

      <form
        className="border-t border-line p-4"
        onSubmit={(e) => {
          e.preventDefault();
          const input = e.currentTarget.elements.namedItem("q") as HTMLInputElement;
          if (input.value.trim() && !busy) { onSubmit(input.value.trim()); input.value = ""; }
        }}
      >
        <input
          name="q"
          disabled={busy}
          placeholder={deepMode ? "提出一个需要多篇论文取证的研究问题…" : "就已入库文献提问…"}
          className="w-full rounded-lg border border-line bg-surface px-4 py-3 text-sm outline-none focus:border-accent"
        />
      </form>
    </section>
  );
}
