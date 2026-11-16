/**
 * 通用 SSE 读取器：用 fetch + ReadableStream 解析 text/event-stream。
 * 比原生 EventSource 灵活（可带 POST body、JWT header）。
 */
export type SSEEvent = { event: string; data: string };

export async function* streamSSE(
  url: string,
  init?: RequestInit,
): AsyncGenerator<SSEEvent> {
  const res = await fetch(url, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
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
      let data = "";
      for (const line of chunk.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) yield { event, data };
    }
  }
}
