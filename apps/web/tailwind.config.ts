import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // 对齐 PRD 设计稿的暗色主题
        bg: "#0a0c11",
        surface: "#12161f",
        line: "rgba(255,255,255,.08)",
        accent: "#8b6cff",
        cyan: "#22d3ee",
      },
    },
  },
  plugins: [],
};
export default config;
