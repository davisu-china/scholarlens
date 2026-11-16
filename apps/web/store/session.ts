import { create } from "zustand";
import type { Claim, Evidence } from "@/lib/types";

interface Message {
  role: "user" | "assistant";
  text: string;
  claims?: Claim[];
  trust?: number;
}

interface SessionState {
  messages: Message[];
  evidence: Record<string, Evidence>;
  selectedEid: string | null;
  deepMode: boolean;
  model: string | null;
  pushMessage: (m: Message) => void;
  updateLast: (patch: Partial<Message>) => void;
  setEvidence: (e: Record<string, Evidence>) => void;
  selectEvidence: (eid: string | null) => void;
  setDeepMode: (v: boolean) => void;
  setModel: (m: string | null) => void;
}

export const useSession = create<SessionState>((set) => ({
  messages: [],
  evidence: {},
  selectedEid: null,
  deepMode: false,
  model: null,
  pushMessage: (m) => set((s) => ({ messages: [...s.messages, m] })),
  updateLast: (patch) =>
    set((s) => {
      const msgs = s.messages.slice();
      if (msgs.length) msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], ...patch };
      return { messages: msgs };
    }),
  setEvidence: (e) => set({ evidence: e }),
  selectEvidence: (eid) => set({ selectedEid: eid }),
  setDeepMode: (v) => set({ deepMode: v }),
  setModel: (m) => set({ model: m }),
}));
