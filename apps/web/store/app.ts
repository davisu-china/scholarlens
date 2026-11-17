"use client";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { AssistantMessage, Message, Mode, Session } from "@/lib/types";
import { uid } from "@/lib/utils";

const MAX_SESSIONS = 40;

/** 右侧面板：要么看某条回答的证据，要么读某篇论文。 */
export type Panel =
  | { kind: "evidence"; sessionId: string; messageId: string; eid: string | null }
  | { kind: "paper"; paperId: string }
  | null;

interface AppState {
  sessions: Session[];
  currentId: string | null;
  mode: Mode;
  model: string | null;
  collection: string | null; // 提问范围；null = 全部文献
  theme: "light" | "dark";
  sidebarOpen: boolean;
  panel: Panel;
  plansOpen: boolean;   // 套餐弹窗
  uploadOpen: boolean;  // 导入弹窗

  newSession: () => void;
  openSession: (id: string) => void;
  renameSession: (id: string, title: string) => void;
  deleteSession: (id: string) => void;
  /** 追加消息；没有当前会话时新建一个。返回会话 id。 */
  append: (msgs: Message[], title?: string) => string;
  patchMessage: (sessionId: string, messageId: string, patch: Partial<AssistantMessage> | ((m: AssistantMessage) => Partial<AssistantMessage>)) => void;

  setMode: (m: Mode) => void;
  setModel: (m: string | null) => void;
  setCollection: (c: string | null) => void;
  setTheme: (t: "light" | "dark") => void;
  setSidebarOpen: (v: boolean) => void;
  setPanel: (p: Panel) => void;
  setPlansOpen: (v: boolean) => void;
  setUploadOpen: (v: boolean) => void;
}

export const useApp = create<AppState>()(
  persist(
    (set, get) => ({
      sessions: [],
      currentId: null,
      mode: "qa",
      model: null,
      collection: null,
      theme: "light",
      sidebarOpen: true,
      panel: null,
      plansOpen: false,
      uploadOpen: false,

      newSession: () => set({ currentId: null, panel: null }),
      openSession: (id) => set({ currentId: id, panel: null }),
      renameSession: (id, title) =>
        set((s) => ({ sessions: s.sessions.map((x) => (x.id === id ? { ...x, title } : x)) })),
      deleteSession: (id) =>
        set((s) => ({
          sessions: s.sessions.filter((x) => x.id !== id),
          currentId: s.currentId === id ? null : s.currentId,
          panel: s.panel?.kind === "evidence" && s.panel.sessionId === id ? null : s.panel,
        })),

      append: (msgs, title) => {
        const now = Date.now();
        let id = get().currentId;
        if (!id || !get().sessions.some((x) => x.id === id)) {
          id = uid();
          const session: Session = { id, title: title ?? "新对话", createdAt: now, updatedAt: now, messages: msgs };
          set((s) => ({ sessions: [session, ...s.sessions].slice(0, MAX_SESSIONS), currentId: id }));
          return id;
        }
        set((s) => ({
          sessions: s.sessions
            .map((x) => (x.id === id ? { ...x, updatedAt: now, messages: [...x.messages, ...msgs] } : x))
            .sort((a, b) => b.updatedAt - a.updatedAt),
        }));
        return id;
      },

      patchMessage: (sessionId, messageId, patch) =>
        set((s) => ({
          sessions: s.sessions.map((x) =>
            x.id !== sessionId
              ? x
              : {
                  ...x,
                  messages: x.messages.map((m) =>
                    m.id === messageId && m.role === "assistant"
                      ? { ...m, ...(typeof patch === "function" ? patch(m) : patch) }
                      : m,
                  ),
                },
          ),
        })),

      setMode: (mode) => set({ mode }),
      setModel: (model) => set({ model }),
      setCollection: (collection) => set({ collection }),
      setTheme: (theme) => set({ theme }),
      setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
      setPanel: (panel) => set({ panel }),
      setPlansOpen: (plansOpen) => set({ plansOpen }),
      setUploadOpen: (uploadOpen) => set({ uploadOpen }),
    }),
    {
      name: "scholarlens",
      version: 1,
      partialize: (s) => ({
        sessions: s.sessions, currentId: s.currentId, mode: s.mode, model: s.model,
        collection: s.collection, theme: s.theme, sidebarOpen: s.sidebarOpen,
      }),
      // 刷新后不可能还在生成：把中断的回答标成"已停止"，避免永远转圈
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        state.sessions = state.sessions.map((x) => ({
          ...x,
          messages: x.messages.map((m) =>
            m.role === "assistant" && ["planning", "running", "streaming"].includes(m.status)
              ? { ...m, status: "stopped" as const }
              : m,
          ),
        }));
      },
    },
  ),
);

export const useCurrentSession = () =>
  useApp((s) => s.sessions.find((x) => x.id === s.currentId) ?? null);
