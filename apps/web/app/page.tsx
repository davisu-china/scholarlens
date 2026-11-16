import { KnowledgePanel } from "@/components/knowledge-panel";
import { ConversationPanel } from "@/components/conversation-panel";
import { EvidencePanel } from "@/components/evidence-panel";

/**
 * 三栏主界面（PRD 第 04 章）：
 *   左 = 知识库 / 会话  ·  中 = 对话 + 研究过程  ·  右 = 证据面板 + PDF 原文
 */
export default function Home() {
  return (
    <main className="grid h-screen grid-cols-[272px_1fr_380px] divide-x divide-line">
      <KnowledgePanel />
      <ConversationPanel />
      <EvidencePanel />
    </main>
  );
}
