import type { Metadata } from "next";
import "katex/dist/katex.min.css";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "ScholarLens · 每一句都能核查的科研助手",
  description: "在你自己的文献库上提问和做深度研究，每个结论都能点回原文位置。",
};

// 首屏前就应用主题，避免深色模式闪白
const themeScript = `try{var s=JSON.parse(localStorage.getItem("scholarlens")||"{}");if(s.state&&s.state.theme==="dark")document.documentElement.classList.add("dark")}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
