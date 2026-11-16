import * as React from "react";
import { cn } from "@/lib/utils";

export const Button = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "ghost" | "outline" }
>(({ className, variant = "default", ...props }, ref) => (
  <button
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50",
      variant === "default" && "bg-accent text-white hover:bg-accent/90",
      variant === "outline" && "border border-line hover:bg-white/5",
      variant === "ghost" && "hover:bg-white/5",
      className,
    )}
    {...props}
  />
));
Button.displayName = "Button";
