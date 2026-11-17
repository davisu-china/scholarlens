"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import * as Menu from "@radix-ui/react-dropdown-menu";
import { BookOpen, ChevronsUpDown, LogOut, MessageSquare, Moon, MoreHorizontal, PanelLeftClose, Pencil, SquarePen, Sun, Trash2 } from "lucide-react";
import { getUsername, signOut } from "@/lib/auth";
import { useBilling, usePapers } from "@/lib/hooks";
import type { QuotaRow, Session } from "@/lib/types";
import { cn, relativeDay } from "@/lib/utils";
import { useApp } from "@/store/app";
import { Logo } from "@/components/logo";
import { Tip } from "@/components/ui/tip";

const menuCls = "z-50 min-w-[168px] rounded-xl border bg-surface p-1 shadow-pop animate-fade-up";
const itemCls = "flex cursor-default select-none items-center gap-2 rounded-lg px-2.5 py-2 text-[13px] outline-none data-[highlighted]:bg-fg/5";

export function Sidebar() {
  const path = usePathname();
  const router = useRouter();
  const { sessions, currentId, newSession, openSession, setSidebarOpen } = useApp();
  const { data: papers } = usePapers();
  const onChat = path === "/";

  const groups: [string, Session[]][] = [];
  for (const s of sessions) {
    const g = relativeDay(s.updatedAt);
    const last = groups[groups.length - 1];
    if (last && last[0] === g) last[1].push(s);
    else groups.push([g, [s]]);
  }

  const startNew = () => { newSession(); if (!onChat) router.push("/"); if (window.innerWidth < 1024) setSidebarOpen(false); };
  const nav = "flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-sm transition-colors";

  return (
    <aside aria-label="导航" className="flex h-full w-[264px] shrink-0 flex-col border-r bg-surface2">
      <div className="flex h-14 items-center justify-between pl-4 pr-2">
        <Link href="/" onClick={newSession} aria-label="ScholarLens 首页"><Logo className="text-[15px]" /></Link>
        <Tip label="收起侧栏">
          <button type="button" aria-label="收起侧栏" onClick={() => setSidebarOpen(false)} className="grid h-8 w-8 place-items-center rounded-full text-fg3 hover:bg-fg/5 hover:text-fg">
            <PanelLeftClose size={16} />
          </button>
        </Tip>
      </div>

      <nav className="space-y-0.5 px-2">
        <button type="button" onClick={startNew} className={cn(nav, "w-full text-fg hover:bg-fg/5")}>
          <SquarePen size={16} className="text-fg2" /> 新对话
        </button>
        <Link href="/library" className={cn(nav, path.startsWith("/library") ? "bg-fg/[0.07] font-medium text-fg" : "text-fg hover:bg-fg/5")}>
          <BookOpen size={16} className="text-fg2" /> 文献库
          {papers && papers.length > 0 && <span className="ml-auto text-xs text-fg3">{papers.length}</span>}
        </Link>
      </nav>

      <div className="mt-4 min-h-0 flex-1 overflow-y-auto px-2 pb-2">
        {sessions.length === 0 ? (
          <div className="px-2.5 py-2 text-[13px] leading-relaxed text-fg3">
            <MessageSquare size={15} className="mb-1.5" />
            对话记录会保存在这台设备上，方便回头查看。
          </div>
        ) : (
          groups.map(([label, list]) => (
            <div key={label} className="mb-3">
              <div className="px-2.5 pb-1 text-xs text-fg3">{label}</div>
              {list.map((s) => (
                <SessionRow key={s.id} s={s} active={onChat && s.id === currentId}
                  onOpen={() => { openSession(s.id); if (!onChat) router.push("/"); if (window.innerWidth < 1024) setSidebarOpen(false); }} />
              ))}
            </div>
          ))
        )}
      </div>

      <UsageCard />
      <AccountMenu />
    </aside>
  );
}

function SessionRow({ s, active, onOpen }: { s: Session; active: boolean; onOpen: () => void }) {
  const { renameSession, deleteSession } = useApp();
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  if (editing) {
    return (
      <input
        autoFocus
        defaultValue={s.title}
        aria-label="重命名对话"
        onBlur={(e) => { renameSession(s.id, e.target.value.trim() || s.title); setEditing(false); }}
        onKeyDown={(e) => {
          if (e.key === "Enter") e.currentTarget.blur();
          if (e.key === "Escape") setEditing(false);
        }}
        className="h-9 w-full rounded-lg border border-accent bg-surface px-2.5 text-[13px] outline-none"
      />
    );
  }
  return (
    <div className={cn("group relative flex h-9 items-center rounded-lg text-[13px] transition-colors", active ? "bg-fg/[0.07] font-medium" : "hover:bg-fg/5")}>
      <button type="button" onClick={onOpen} className="h-full min-w-0 flex-1 truncate pl-2.5 pr-1 text-left" title={s.title}>{s.title}</button>
      <Menu.Root onOpenChange={(o) => !o && setConfirming(false)}>
        <Menu.Trigger aria-label="对话操作" className="mr-1 grid h-7 w-7 shrink-0 place-items-center rounded-full text-fg3 opacity-0 hover:bg-fg/10 hover:text-fg focus-visible:opacity-100 group-hover:opacity-100 data-[state=open]:opacity-100">
          <MoreHorizontal size={15} />
        </Menu.Trigger>
        <Menu.Portal>
          <Menu.Content align="start" sideOffset={4} className={menuCls}>
            <Menu.Item className={itemCls} onSelect={() => setEditing(true)}><Pencil size={14} /> 重命名</Menu.Item>
            <Menu.Item className={cn(itemCls, "text-bad")}
              onSelect={(e) => { if (!confirming) { e.preventDefault(); setConfirming(true); } else deleteSession(s.id); }}>
              <Trash2 size={14} /> {confirming ? "再点一次确认删除" : "删除"}
            </Menu.Item>
          </Menu.Content>
        </Menu.Portal>
      </Menu.Root>
    </div>
  );
}

const QUOTA_LABEL: Record<string, string> = { query: "快速问答", research: "深度研究", ingest_pages: "解析页数" };
const WINDOW_LABEL: Record<string, string> = { day: "今日", month: "本月" };

function UsageCard() {
  const { data } = useBilling();
  const setPlansOpen = useApp((s) => s.setPlansOpen);
  if (!data) return null;
  const rows = data.quotas.filter((q) => q.limit != null);
  const free = data.plan.id === "free";
  return (
    <div className="mx-2 mb-1 rounded-xl border bg-surface p-3">
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-medium">{data.plan.name}</span>
        <button type="button" onClick={() => setPlansOpen(true)} className="text-xs text-accent hover:underline">
          {free ? "升级" : "套餐详情"}
        </button>
      </div>
      {rows.length > 0 ? (
        <ul className="mt-2.5 space-y-2">{rows.map((q) => <QuotaBar key={q.action + q.window} q={q} />)}</ul>
      ) : (
        <p className="mt-1 text-xs text-fg3">用量不限</p>
      )}
    </div>
  );
}

function QuotaBar({ q }: { q: QuotaRow }) {
  const limit = q.limit ?? 0;
  const ratio = limit ? Math.min(1, q.used / limit) : 0;
  return (
    <li>
      <div className="flex justify-between text-xs text-fg2">
        <span>{WINDOW_LABEL[q.window] ?? ""}{QUOTA_LABEL[q.action] ?? q.action}</span>
        <span className={cn("tabular-nums", ratio >= 1 ? "text-bad" : "text-fg3")}>{q.used} / {limit}</span>
      </div>
      <div className="mt-1 h-1 overflow-hidden rounded-full bg-fg/[0.07]" role="progressbar" aria-valuenow={q.used} aria-valuemax={limit}>
        <div className={cn("h-full rounded-full", ratio >= 1 ? "bg-bad" : ratio >= 0.8 ? "bg-warn" : "bg-accent")} style={{ width: `${ratio * 100}%` }} />
      </div>
    </li>
  );
}

function AccountMenu() {
  const { theme, setTheme } = useApp();
  const name = getUsername() ?? "账户";
  return (
    <Menu.Root>
      <Menu.Trigger className="m-2 flex h-11 items-center gap-2.5 rounded-xl px-2 text-left text-[13px] hover:bg-fg/5 data-[state=open]:bg-fg/5">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-accent-soft text-xs font-semibold uppercase text-accent">{name.slice(0, 1)}</span>
        <span className="min-w-0 flex-1 truncate font-medium">{name}</span>
        <ChevronsUpDown size={14} className="text-fg3" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Content side="top" align="start" sideOffset={6} className={cn(menuCls, "w-[244px]")}>
          <Menu.Item className={itemCls} onSelect={() => setTheme(theme === "dark" ? "light" : "dark")}>
            {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />} {theme === "dark" ? "切换到浅色" : "切换到深色"}
          </Menu.Item>
          <Menu.Separator className="my-1 h-px bg-line" />
          <Menu.Item className={itemCls} onSelect={() => signOut()}><LogOut size={14} /> 退出登录</Menu.Item>
        </Menu.Content>
      </Menu.Portal>
    </Menu.Root>
  );
}
