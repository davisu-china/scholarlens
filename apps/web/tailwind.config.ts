import type { Config } from "tailwindcss";

const v = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: v("bg"),
        surface: v("surface"),
        surface2: v("surface-2"),
        line: v("line"),
        fg: v("fg"),
        fg2: v("fg-2"),
        fg3: v("fg-3"),
        accent: v("accent"),
        "accent-soft": v("accent-soft"),
        ok: v("ok"),
        warn: v("warn"),
        bad: v("bad"),
        mark: v("mark"),
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", '"SF Pro Text"', "Inter", '"PingFang SC"', '"HarmonyOS Sans SC"', '"Microsoft YaHei"', "system-ui", "sans-serif"],
        mono: ['"SF Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgb(0 0 0 / 0.04), 0 0 0 0.5px rgb(0 0 0 / 0.04)",
        pop: "0 12px 32px rgb(0 0 0 / 0.14), 0 0 0 0.5px rgb(0 0 0 / 0.08)",
      },
      keyframes: {
        "fade-up": { from: { opacity: "0", transform: "translateY(6px)" }, to: { opacity: "1", transform: "none" } },
        "slide-in": { from: { opacity: "0", transform: "translateX(16px)" }, to: { opacity: "1", transform: "none" } },
        blink: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0" } },
      },
      animation: {
        "fade-up": "fade-up .28s cubic-bezier(.22,1,.36,1) both",
        "slide-in": "slide-in .28s cubic-bezier(.22,1,.36,1) both",
        blink: "blink 1s step-end infinite",
      },
    },
  },
  plugins: [],
};
export default config;
