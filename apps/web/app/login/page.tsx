"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Eye, EyeOff, FileSearch, Loader2, ShieldCheck, Telescope } from "lucide-react";
import { getToken, signIn } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";

const POINTS = [
  { icon: FileSearch, title: "点一下就能核对", text: "回答里的每个引用都能跳到论文的具体页面，并高亮对应的段落。" },
  { icon: ShieldCheck, title: "生成后逐句校验", text: "引用的原文不足以支持某句话时，会明确标出来，不会悄悄带过。" },
  { icon: Telescope, title: "多篇论文的深度研究", text: "先给出研究计划让你修改，再多轮检索，写成带引用的综述。" },
];

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { if (getToken()) router.replace("/"); }, [router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const name = username.trim();
    if (name.length < 2) return setError("用户名至少 2 个字符");
    if (password.length < 6) return setError("密码至少 6 位");
    setBusy(true); setError(null);
    try {
      await signIn(mode, name, password);
      window.location.replace("/");
    } catch (err) {
      setError((err as Error).message || "出错了，请重试");
      setBusy(false);
    }
  }

  const input = "h-11 w-full rounded-xl border bg-surface px-3.5 text-[15px] outline-none transition-colors placeholder:text-fg3 focus:border-accent";

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden overflow-hidden bg-[#070d18] text-white lg:flex lg:flex-col lg:justify-between lg:p-14">
        <div aria-hidden className="pointer-events-none absolute inset-0"
          style={{ background: "radial-gradient(700px 480px at 85% 0%, rgba(77,163,255,.28), transparent 62%), radial-gradient(620px 420px at 0% 100%, rgba(143,182,255,.16), transparent 60%)" }} />
        <Logo className="relative text-base text-white" />
        <div className="relative max-w-[460px]">
          <h1 className="text-[44px] font-semibold leading-[1.15] tracking-tight">
            每一句结论，<br /><span className="bg-gradient-to-r from-[#8fb6ff] to-[#4da3ff] bg-clip-text text-transparent">都能点回原文。</span>
          </h1>
          <p className="mt-5 text-[16px] leading-relaxed text-white/70">在你自己的论文库上提问、做文献综述。省下来的是一条条翻原文核对的时间。</p>
          <ul className="mt-10 space-y-6">
            {POINTS.map(({ icon: Icon, title, text }) => (
              <li key={title} className="flex gap-4">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl border border-white/10 bg-white/[0.06]"><Icon size={18} className="text-[#8fb6ff]" /></span>
                <div>
                  <div className="text-[15px] font-medium">{title}</div>
                  <div className="mt-0.5 text-sm leading-relaxed text-white/60">{text}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-white/40">上传的论文只用于回答你自己的问题。</p>
      </section>

      <section className="flex items-center justify-center bg-surface px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-[360px]" noValidate>
          <Logo className="mb-10 text-base lg:hidden" />
          <h2 className="text-[26px] font-semibold tracking-tight">{mode === "login" ? "登录" : "创建账户"}</h2>
          <p className="mt-1.5 text-sm text-fg2">{mode === "login" ? "继续你的文献研究。" : "注册后即可导入论文开始使用。"}</p>

          <label htmlFor="username" className="mt-8 block text-[13px] font-medium">用户名</label>
          <input id="username" className={cn(input, "mt-1.5")} autoComplete="username" autoFocus value={username} onChange={(e) => setUsername(e.target.value)} />

          <label htmlFor="password" className="mt-4 block text-[13px] font-medium">密码</label>
          <div className="relative mt-1.5">
            <input id="password" className={cn(input, "pr-11")} type={show ? "text" : "password"}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              placeholder={mode === "register" ? "至少 6 位" : undefined}
              value={password} onChange={(e) => setPassword(e.target.value)} />
            <button type="button" aria-label={show ? "隐藏密码" : "显示密码"} onClick={() => setShow((v) => !v)}
              className="absolute right-1.5 top-1/2 grid h-8 w-8 -translate-y-1/2 place-items-center rounded-full text-fg3 hover:bg-fg/5 hover:text-fg">
              {show ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>

          {error && <p className="mt-3 text-[13px] text-bad" role="alert">{error}</p>}

          <Button type="submit" variant="primary" size="lg" className="mt-6 w-full" disabled={busy}>
            {busy && <Loader2 size={16} className="animate-spin" />}
            {mode === "login" ? "登录" : "注册并登录"}
          </Button>

          <p className="mt-6 text-center text-sm text-fg2">
            {mode === "login" ? "还没有账户？" : "已经有账户？"}
            <button type="button" className="ml-1 font-medium text-accent hover:underline"
              onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}>
              {mode === "login" ? "注册" : "直接登录"}
            </button>
          </p>
        </form>
      </section>
    </div>
  );
}
