import type { Claim, Evidence } from "./types";

const CITE = /\[\s*([A-Za-z][\w-]*(?:\s*[,，、;]\s*[A-Za-z][\w-]*)*)\s*\]/g;

const isEid = (id: string, evidence?: Record<string, Evidence>) =>
  evidence && Object.keys(evidence).length ? id in evidence : /^e\d+$/.test(id);

/** 证据在正文中首次出现的顺序 → 显示用的序号（1 起）。 */
export function citeOrder(text: string, evidence?: Record<string, Evidence>): Map<string, number> {
  const order = new Map<string, number>();
  for (const m of text.matchAll(CITE)) {
    const ids = m[1].split(/[,，、;]/).map((s) => s.trim());
    if (!ids.every((id) => isEid(id, evidence))) continue;
    for (const id of ids) if (!order.has(id)) order.set(id, order.size + 1);
  }
  return order;
}

// 紧跟在引用后面的标点一起带上，渲染时和角标绑在一起，避免标点单独掉到下一行
const CITE_PUNCT = new RegExp(CITE.source + "([。，；、,.;:：！？!?])?", "g");

export const citeHref = (eid: string, ok: boolean, punct = "") =>
  `#cite~${encodeURIComponent(eid)}~${ok ? "o" : "x"}~${encodeURIComponent(punct)}`;

export function parseCiteHref(href?: string): { eid: string; ok: boolean; punct: string } | null {
  if (!href?.startsWith("#cite~")) return null;
  const [, eid, flag, punct = ""] = href.split("~");
  return { eid: decodeURIComponent(eid), ok: flag !== "x", punct: decodeURIComponent(punct) };
}

/**
 * 把正文里的 [e1] / [e1, e2] 换成 Markdown 链接，渲染时再变成引用角标。
 * 校验结果按出现顺序对应到每个角标：同一条证据可能支持一句、不支持另一句。
 */
export function linkCitations(text: string, evidence?: Record<string, Evidence>, claims?: Claim[]): string {
  const order = citeOrder(text, evidence);
  const queue = (claims ?? []).flatMap((c) => c.eids.map((eid) => ({ eid, ok: c.supported })));
  let ptr = 0;
  return text.replace(CITE_PUNCT, (whole, inner: string, punct: string | undefined) => {
    const ids = inner.split(/[,，、;]/).map((s) => s.trim());
    if (!ids.every((id) => order.has(id))) return whole;
    return ids
      .map((id, k) => {
        let ok = true;
        const i = queue.findIndex((q, k) => k >= ptr && q.eid === id);
        if (i >= 0) { ok = queue[i].ok; ptr = i + 1; }
        return `[${order.get(id)}](${citeHref(id, ok, k === ids.length - 1 ? punct : "")})`;
      })
      .join("");
  });
}

export const firstPage = (ev?: Evidence) => ev?.provenance.bboxes?.[0]?.page;
