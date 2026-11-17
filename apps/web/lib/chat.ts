"use client";
import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { askQuestion, describeError, planResearch, resumeResearch } from "./api";
import type { AssistantMessage } from "./types";
import { uid } from "./utils";
import { useApp } from "@/store/app";

// 每条进行中的回答对应一个 AbortController，用于"停止"
const controllers = new Map<string, AbortController>();

const isAbort = (e: unknown) => (e as Error)?.name === "AbortError";

export function stopMessage(sessionId: string, messageId: string) {
  controllers.get(messageId)?.abort();
  controllers.delete(messageId);
  useApp.getState().patchMessage(sessionId, messageId, (m) =>
    ["planning", "running", "streaming"].includes(m.status) ? { status: "stopped" } : {},
  );
}

export function useChat() {
  const qc = useQueryClient();
  const refreshUsage = useCallback(() => qc.invalidateQueries({ queryKey: ["billing"] }), [qc]);

  const fail = useCallback((sid: string, mid: string, e: unknown) => {
    if (isAbort(e)) return;
    const { message, status } = describeError(e);
    useApp.getState().patchMessage(sid, mid, { status: "error", error: message, errorStatus: status });
  }, []);

  const runQA = useCallback(async (sid: string, mid: string, question: string) => {
    const { patchMessage, collection, model } = useApp.getState();
    const ac = new AbortController();
    controllers.set(mid, ac);
    patchMessage(sid, mid, { status: "streaming", text: "", error: undefined, claims: undefined, trust: undefined });
    try {
      let acc = "";
      let finished = false;
      await askQuestion(question, {
        collection, model, signal: ac.signal,
        onToken: (t) => { acc += t; patchMessage(sid, mid, { text: acc }); },
        onDone: (d) => {
          finished = true;
          patchMessage(sid, mid, { status: "done", claims: d.claims, trust: d.trust, evidence: d.evidence ?? {} });
        },
      });
      if (!finished) patchMessage(sid, mid, { status: acc ? "done" : "error", error: acc ? undefined : "没有收到回答，请重试" });
    } catch (e) {
      fail(sid, mid, e);
    } finally {
      controllers.delete(mid);
      refreshUsage();
    }
  }, [fail, refreshUsage]);

  const runPlan = useCallback(async (sid: string, mid: string, question: string) => {
    const { patchMessage, collection, model } = useApp.getState();
    const ac = new AbortController();
    controllers.set(mid, ac);
    patchMessage(sid, mid, { status: "planning", error: undefined });
    try {
      const { thread_id, plan } = await planResearch(question, { collection, model, signal: ac.signal });
      patchMessage(sid, mid, { status: "plan", threadId: thread_id, plan });
    } catch (e) {
      fail(sid, mid, e);
    } finally {
      controllers.delete(mid);
    }
  }, [fail]);

  /** 发送一个新问题。 */
  const send = useCallback((question: string) => {
    const { append, mode } = useApp.getState();
    const mid = uid();
    const assistant: AssistantMessage = {
      id: mid, role: "assistant", mode, question, text: "",
      status: mode === "qa" ? "streaming" : "planning",
    };
    const sid = append([{ id: uid(), role: "user", text: question }, assistant], question.slice(0, 40));
    if (mode === "qa") void runQA(sid, mid, question);
    else void runPlan(sid, mid, question);
  }, [runQA, runPlan]);

  /** 深度研究：用户确认（可能编辑过的）计划后开始执行。 */
  const confirmPlan = useCallback(async (sid: string, mid: string, threadId: string, plan: string[]) => {
    const { patchMessage } = useApp.getState();
    const ac = new AbortController();
    controllers.set(mid, ac);
    patchMessage(sid, mid, { status: "running", plan, trace: [], error: undefined });
    try {
      let finished = false;
      await resumeResearch(threadId, plan, {
        signal: ac.signal,
        onTrace: (ev) => patchMessage(sid, mid, (m) => ({ trace: [...(m.trace ?? []), ev] })),
        onAnswer: (a) => {
          finished = true;
          patchMessage(sid, mid, {
            status: "done", text: a.answer, claims: a.claims, trust: a.trust,
            coverage: a.coverage, evidence: a.evidence ?? {},
          });
        },
      });
      if (!finished) patchMessage(sid, mid, { status: "error", error: "研究没有返回结果，请重试" });
    } catch (e) {
      fail(sid, mid, e);
    } finally {
      controllers.delete(mid);
      refreshUsage();
    }
  }, [fail, refreshUsage]);

  /** 出错或停止后重试同一个问题。 */
  const retry = useCallback((sid: string, m: AssistantMessage) => {
    if (m.mode === "qa") void runQA(sid, m.id, m.question);
    else void runPlan(sid, m.id, m.question);
  }, [runQA, runPlan]);

  return { send, confirmPlan, retry };
}
