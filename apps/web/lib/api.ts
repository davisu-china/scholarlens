import { streamSSE, type SSEEvent } from "./sse";

/** 快速问答：流式返回 token / done。对应后端 POST /query。 */
export function askQuestion(question: string, collection?: string): AsyncGenerator<SSEEvent> {
  return streamSSE("/api/query", {
    method: "POST",
    body: JSON.stringify({ question, collection }),
  });
}

/** 深度研究：流式返回 plan / trace / answer。对应后端 POST /research。 */
export function deepResearch(question: string, approvedPlan?: unknown[]): AsyncGenerator<SSEEvent> {
  return streamSSE("/api/research", {
    method: "POST",
    body: JSON.stringify({ question, approved_plan: approvedPlan }),
  });
}
