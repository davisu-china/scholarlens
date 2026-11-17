"use client";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { Loader2 } from "lucide-react";
import { fetchCitationGraph } from "@/lib/api";
import { usePaperTitles } from "@/lib/hooks";
import { useApp } from "@/store/app";

const short = (s: string) => (s.length > 26 ? s.slice(0, 26) + "…" : s);

/** 引用关系图：中心是当前论文，周围是与它有引用关系的论文。 */
export default function CitationGraph({ paperId }: { paperId: string }) {
  const { data, isLoading, isError } = useQuery({ queryKey: ["graph", paperId], queryFn: () => fetchCitationGraph(paperId) });
  const titleOf = usePaperTitles();
  const dark = useApp((s) => s.theme === "dark");

  const option = useMemo(() => {
    if (!data) return null;
    const ink = dark ? "#f0f2f7" : "#1d1d1f";
    const accent = dark ? "#4da3ff" : "#0066e6";
    return {
      backgroundColor: "transparent",
      tooltip: { formatter: (p: { data: { full?: string } }) => p.data.full ?? "" },
      series: [{
        type: "graph", layout: "force", roam: true, draggable: true,
        label: { show: true, position: "bottom", color: ink, fontSize: 11, formatter: (p: { data: { name: string } }) => p.data.name },
        force: { repulsion: 260, edgeLength: 110 },
        data: data.nodes.map((n) => ({
          id: n.id, name: short(titleOf(n.id)), full: titleOf(n.id),
          symbolSize: n.seed ? 30 : 16,
          itemStyle: { color: n.seed ? accent : dark ? "#707a8c" : "#a1a1a6" },
        })),
        edges: data.edges.map((e) => ({ source: e.source, target: e.target })),
        lineStyle: { color: dark ? "rgba(255,255,255,.25)" : "rgba(0,0,0,.2)", curveness: 0.12 },
      }],
    };
  }, [data, titleOf, dark]);

  if (isLoading) return <div className="flex h-full items-center justify-center gap-2 text-[13px] text-fg3"><Loader2 size={15} className="animate-spin" /> 正在加载引用关系…</div>;
  if (isError) return <div className="flex h-full items-center justify-center p-6 text-[13px] text-fg2">引用关系加载失败</div>;
  if (!data || data.nodes.length <= 1) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-1 p-8 text-center text-[13px] text-fg2">
        <span className="font-medium text-fg">还没有引用关系</span>
        这篇论文和库里其他论文之间暂时没有发现引用。导入它引用的论文后，这里会显示关系图。
      </div>
    );
  }
  return <ReactECharts option={option!} style={{ height: "100%", width: "100%" }} notMerge />;
}
