import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36);

export function relativeDay(ts: number): "今天" | "昨天" | "近 7 天" | "更早" {
  const start = new Date(); start.setHours(0, 0, 0, 0);
  const d = (start.getTime() - ts) / 86400000;
  if (d <= 0) return "今天";
  if (d <= 1) return "昨天";
  if (d <= 7) return "近 7 天";
  return "更早";
}
