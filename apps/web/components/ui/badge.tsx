import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({
  className, tone = "default", ...props
}: React.HTMLAttributes<HTMLSpanElement> & { tone?: "default" | "ok" | "warn" | "bad" | "accent" }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        tone === "default" && "bg-fg/5 text-fg2",
        tone === "ok" && "bg-ok/10 text-ok",
        tone === "warn" && "bg-warn/10 text-warn",
        tone === "bad" && "bg-bad/10 text-bad",
        tone === "accent" && "bg-accent-soft text-accent",
        className,
      )}
      {...props}
    />
  );
}
