"use client";
import { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";
import { fetchCitationGraph } from "@/lib/api";

/** 引用图谱（PRD F6）：力导向图，节点大小表示库内被引次数。 */
export function CitationGraph({ paperId }: { paperId: string }) {
  const [option, setOption] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    fetchCitationGraph(paperId).then((g) => {
      setOption({
        backgroundColor: "transparent",
        series: [
          {
            type: "graph",
            layout: "force",
            roam: true,
            label: { show: true, color: "#e7e9ef" },
            force: { repulsion: 120, edgeLength: 90 },
            data: g.nodes.map((n) => ({
              name: n.id,
              symbolSize: n.seed ? 40 : 24,
              itemStyle: { color: n.seed ? "#8b6cff" : "#22d3ee" },
            })),
            edges: g.edges.map((e) => ({ source: e.source, target: e.target })),
            lineStyle: { color: "rgba(255,255,255,.25)", curveness: 0.15 },
          },
        ],
      });
    });
  }, [paperId]);

  if (!option) return <div className="p-6 text-sm text-[#98a1b3]">加载引用图谱…</div>;
  return <ReactECharts option={option} style={{ height: "100%", width: "100%" }} />;
}
