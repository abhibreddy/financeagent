import { AgentChat } from "@/components/agent-chat";

export default function FinanceChat() {
  return (
    <AgentChat
      endpoint="/api/agents/finance/stream"
      title="Agent Chat"
      subtitle="Fraud investigation · Data → Audit → Synthesis · Azure OpenAI"
      avatar="🛡️"
      suggestions={[
        "Investigate ACC-00009",
        "Why is ACC-00043 flagged?",
        "Is ACC-00054 safe to clear?",
      ]}
    />
  );
}
