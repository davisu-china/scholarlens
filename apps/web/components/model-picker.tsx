"use client";
import { useEffect, useState } from "react";
import { fetchModels } from "@/lib/api";
import { useSession } from "@/store/session";

type M = { id: string; label: string; description: string; tier: string };

/** 模型选择器（商业化：让用户在 Opus / DeepSeek 等之间自选）。 */
export function ModelPicker() {
  const { model, setModel } = useSession();
  const [models, setModels] = useState<M[]>([]);

  useEffect(() => {
    fetchModels().then((d) => {
      setModels(d.models);
      if (!model && d.default) setModel(d.default);
    });
  }, [model, setModel]);

  if (!models.length) return null;
  return (
    <label className="flex items-center gap-2 text-xs text-[#98a1b3]">
      模型
      <select
        value={model ?? ""}
        onChange={(e) => setModel(e.target.value)}
        title={models.find((m) => m.id === model)?.description}
        className="rounded-md border border-line bg-surface px-2 py-1 text-[#e7e9ef] outline-none focus:border-accent"
      >
        {models.map((m) => (
          <option key={m.id} value={m.id}>{m.label}</option>
        ))}
      </select>
    </label>
  );
}
