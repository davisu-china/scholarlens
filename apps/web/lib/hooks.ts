"use client";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchBilling, fetchCollections, fetchModels, fetchPapers } from "./api";

export const usePapers = () => useQuery({ queryKey: ["papers"], queryFn: fetchPapers });
export const useCollections = () => useQuery({ queryKey: ["collections"], queryFn: fetchCollections });
export const useBilling = () => useQuery({ queryKey: ["billing"], queryFn: fetchBilling });
export const useModels = () => useQuery({ queryKey: ["models"], queryFn: fetchModels });

/** paper_id → 标题，用于把证据里的 id 显示成人能读的名字。 */
export function usePaperTitles(): (id: string) => string {
  const { data } = usePapers();
  return useMemo(() => {
    const map = new Map((data ?? []).map((p) => [p.paper_id, p.title]));
    return (id: string) => map.get(id) || id;
  }, [data]);
}
