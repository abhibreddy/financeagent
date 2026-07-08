import { AgentChat } from "@/components/agent-chat";

export default function FinanceCopilot() {
  return (
    <AgentChat
      endpoint="/api/agents/suite/copilot/stream"
      title="Finance Copilot"
      subtitle="Cross-functional finance assistant · payables, receivables, cash & insights"
      avatar="🧭"
      suggestions={[
        "Give me a finance health snapshot.",
        "What should I prioritize this week?",
        "Any red flags across AP, AR and cash?",
      ]}
    />
  );
}
