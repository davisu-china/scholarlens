"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { PanelLeftOpen } from "lucide-react";
import { getToken } from "@/lib/auth";
import { useApp } from "@/store/app";
import { Sidebar } from "@/components/sidebar";
import { RightPanel } from "@/components/right-panel";
import { PlansDialog } from "@/components/plans-dialog";
import { UploadDialog } from "@/components/library/upload-dialog";
import { Tip } from "@/components/ui/tip";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const sidebarOpen = useApp((s) => s.sidebarOpen);
  const setSidebarOpen = useApp((s) => s.setSidebarOpen);

  const path = usePathname();
  useEffect(() => {
    if (!getToken()) router.replace("/login");
    else setReady(true);
  }, [router]);
  // 窄屏上侧栏是浮层：进入页面或切换页面后收起，不挡内容
  useEffect(() => {
    if (window.innerWidth < 1024) setSidebarOpen(false);
  }, [path, setSidebarOpen]);

  if (!ready) return null;

  return (
    <div className="flex h-screen overflow-hidden">
      {sidebarOpen && (
        <>
          <div className="fixed inset-0 z-30 bg-black/30 lg:hidden" onClick={() => setSidebarOpen(false)} aria-hidden />
          <div className="fixed inset-y-0 left-0 z-40 lg:static lg:z-auto"><Sidebar /></div>
        </>
      )}
      <main className="relative flex min-w-0 flex-1 flex-col bg-surface">
        {!sidebarOpen && (
          <Tip label="展开侧栏" side="right">
            <button type="button" aria-label="展开侧栏" onClick={() => setSidebarOpen(true)}
              className="absolute left-3 top-3 z-20 grid h-8 w-8 place-items-center rounded-full text-fg3 hover:bg-fg/5 hover:text-fg">
              <PanelLeftOpen size={16} />
            </button>
          </Tip>
        )}
        {children}
      </main>
      <RightPanel />
      <PlansDialog />
      <UploadDialog />
    </div>
  );
}
