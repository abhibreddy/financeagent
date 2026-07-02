import { AgentChat } from "@/components/agent-chat";

export default function TradingAgent() {
  return (
    <AgentChat
      endpoint="/api/agents/trading/stream"
      title="Portfolio Agent"
      subtitle="Portfolio analysis · Data → Audit → Synthesis · Azure OpenAI"
      avatar="📈"
      suggestions={[
        "Analyze portfolio risk",
        "What's my largest concentration?",
        "Should I rebalance?",
      ]}
    />
  );
}
