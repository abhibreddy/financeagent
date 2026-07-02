"use client";

import { useCallback, useRef, useState } from "react";
import { API_URL } from "./api";
import type { ChatMessage } from "./types";

export interface PipelineStage {
  stage: string; // "data" | "ground_truth" | "audit"
  content: string;
}

/**
 * Chat hook backed by a FastAPI SSE endpoint (POST + streamed body).
 * EventSource can't POST a body, so we read the fetch stream and parse SSE frames.
 * Stages arrive as `event: stage` frames (the Data→Audit→Synthesis reveal); the assistant
 * reply arrives as `event: final`.
 */
export function useAgentStream(endpoint: string, analyst = "analyst") {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionId = useRef<string>(crypto.randomUUID());

  const reset = useCallback(() => {
    setMessages([]);
    setStages([]);
    setError(null);
    sessionId.current = crypto.randomUUID();
  }, []);

  const send = useCallback(
    async (text: string) => {
      const userMsg: ChatMessage = { role: "user", content: text };
      const history = [...messages, userMsg];
      setMessages(history);
      setStages([]);
      setError(null);
      setRunning(true);

      try {
        const res = await fetch(`${API_URL}${endpoint}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: history, session_id: sessionId.current, analyst }),
        });
        if (!res.ok || !res.body) throw new Error(`Stream failed (${res.status})`);

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // SSE frames are separated by a blank line; sse-starlette emits CRLF (\r\n\r\n).
          const frames = buffer.split(/\r?\n\r?\n/);
          buffer = frames.pop() ?? "";
          for (const frame of frames) {
            let event = "message";
            let data = "";
            for (const line of frame.split(/\r?\n/)) {
              if (line.startsWith("event:")) event = line.slice(6).trim();
              else if (line.startsWith("data:")) data += line.slice(5).trim();
            }
            if (!data) continue;
            const payload = JSON.parse(data);

            if (event === "stage") {
              setStages((s) => [...s, { stage: payload.stage, content: payload.content }]);
            } else if (event === "final") {
              setMessages([...history, { role: "assistant", content: payload.final }]);
            } else if (event === "error") {
              setError(payload.message ?? "Agent error");
            }
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setRunning(false);
      }
    },
    [messages, endpoint, analyst]
  );

  return { messages, stages, running, error, send, reset, sessionId: sessionId.current };
}
