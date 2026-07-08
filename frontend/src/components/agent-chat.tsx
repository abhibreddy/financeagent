"use client";

import { useMemo, useState } from "react";
import { useAgentStream } from "@/lib/useAgentStream";
import { Markdown } from "@/components/markdown";
import { PageHeader } from "@/components/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

const STAGE_LABELS: Record<string, string> = {
  data: "Data Agent",
  ground_truth: "Ground Truth",
  audit: "Audit Agent",
};

export function AgentChat({
  endpoint,
  title,
  subtitle,
  suggestions,
  avatar = "🤖",
  scenario,
}: {
  endpoint: string;
  title: string;
  subtitle: string;
  suggestions: string[];
  avatar?: string;
  scenario?: string;
}) {
  const extra = useMemo(() => (scenario ? { scenario } : undefined), [scenario]);
  const { messages, stages, running, error, send, reset } = useAgentStream(endpoint, "analyst", extra);
  const [input, setInput] = useState("");

  function submit(text: string) {
    if (!text.trim() || running) return;
    send(text.trim());
    setInput("");
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-3xl flex-col">
      <div className="flex items-start justify-between">
        <PageHeader title={title} subtitle={subtitle} />
        {messages.length > 0 && (
          <Button variant="outline" size="sm" onClick={reset}>
            Clear
          </Button>
        )}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto pb-4">
        {messages.length === 0 && !running && (
          <Card className="p-6">
            <p className="text-sm text-muted-foreground">Try one of these:</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {suggestions.map((s) => (
                <Button key={s} variant="secondary" size="sm" onClick={() => submit(s)}>
                  {s}
                </Button>
              ))}
            </div>
          </Card>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-primary px-4 py-2 text-sm text-primary-foreground">
                {m.content}
              </div>
            </div>
          ) : (
            <div key={i} className="flex gap-3">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted">{avatar}</div>
              <Card className="max-w-[85%] p-4">
                <Markdown>{m.content}</Markdown>
              </Card>
            </div>
          )
        )}

        {running && (
          <div className="flex gap-3">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted">{avatar}</div>
            <Card className="w-full max-w-[85%] p-4">
              <div className="mb-3 flex items-center gap-2 text-sm">
                <span className="inline-block size-2 animate-pulse rounded-full bg-primary" />
                <span className="text-muted-foreground">Running pipeline…</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {["data", "ground_truth", "audit"].map((st) => {
                  const done = stages.some((s) => s.stage === st);
                  return (
                    <Badge key={st} variant={done ? "success" : "secondary"}>
                      {STAGE_LABELS[st]} {done ? "✓" : "…"}
                    </Badge>
                  );
                })}
              </div>
              {stages.map((s, i) => (
                <details key={i} className="mt-2 text-xs">
                  <summary className="cursor-pointer text-muted-foreground">{STAGE_LABELS[s.stage]} output</summary>
                  <pre className="mt-1 whitespace-pre-wrap rounded bg-muted p-2">{s.content}</pre>
                </details>
              ))}
            </Card>
          </div>
        )}

        {error && (
          <Card className="border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">{error}</Card>
        )}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit(input);
        }}
        className="flex gap-2 border-t border-border pt-3"
      >
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your question…"
          disabled={running}
        />
        <Button type="submit" disabled={running || !input.trim()}>
          Send
        </Button>
      </form>
    </div>
  );
}
