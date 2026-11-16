import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className,
  tone = "default",
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: "default" | "ok" | "bad" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium",
        tone === "default" && "bg-white/8 text-[#c7ccd8]",
        tone === "ok" && "bg-emerald-500/15 text-emerald-300",
        tone === "bad" && "bg-red-500/15 text-red-300",
        className,
      )}
      {...props}
    />
  );
}
