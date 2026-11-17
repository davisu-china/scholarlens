"use client";
import * as Tooltip from "@radix-ui/react-tooltip";

/** 悬停提示。 */
export function Tip({ label, children, side = "top" }: { label: React.ReactNode; children: React.ReactNode; side?: "top" | "bottom" | "left" | "right" }) {
  return (
    <Tooltip.Root>
      <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
      <Tooltip.Portal>
        <Tooltip.Content
          side={side}
          sideOffset={6}
          className="z-[60] max-w-xs rounded-lg bg-fg px-2.5 py-1.5 text-xs leading-relaxed text-bg shadow-pop animate-fade-up"
        >
          {label}
        </Tooltip.Content>
      </Tooltip.Portal>
    </Tooltip.Root>
  );
}
