/**
 * 通用 SSE 读取器：用 fetch + ReadableStream 解析 text/event-stream。
 * 比原生 EventSource 灵活（可带 POST body、JWT header）。
 */
import { authFetch } from "./auth";

export type SSEEvent = { event: string; data: string };

export async function* streamSSE(
  url: string,
  init?: RequestInit,
): AsyncGenerator<SSEEvent> {
  const res = await authFetch(url, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  if (!res.body) throw new Error("no response body");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const chunks = buf.split("\n\n");
    buf = chunks.pop() ?? "";
    for (const chunk of chunks) {
      let event = "message";
      const dataLines: string[] = [];
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) {
          event = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          // 按 SSE 规范仅去掉冒号后的一个前导空格，保留 token 内的空白
          dataLines.push(line.slice(5).replace(/^ /, ""));
        }
      }
      if (dataLines.length) yield { event, data: dataLines.join("\n") };
    }
  }
}
