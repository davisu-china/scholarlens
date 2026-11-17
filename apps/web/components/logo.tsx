import { cn } from "@/lib/utils";

export function Logo({ className, size = 22 }: { className?: string; size?: number }) {
  return (
    <span className={cn("inline-flex items-center gap-2 font-semibold tracking-tight", className)}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
        <rect width="24" height="24" rx="6.5" className="fill-accent" />
        <circle cx="10.5" cy="10.5" r="4.6" stroke="white" strokeWidth="1.9" />
        <path d="M14 14l4.2 4.2" stroke="white" strokeWidth="1.9" strokeLinecap="round" />
        <path d="M8.6 10.5h3.8" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      ScholarLens
    </span>
  );
}
