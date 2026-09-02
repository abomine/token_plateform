"use client";

import { useEffect, useRef, useState } from "react";
import { executePrompt, formatCredits } from "@/lib/api";

export default function Playground({ onBalanceChange, onNotify }) {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function onSubmit(e) {
    e.preventDefault();
    const text = prompt.trim();
    if (!text || loading) return;

    setPrompt("");
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: text },
    ]);
    setLoading(true);

    try {
      const result = await executePrompt(text);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.content,
          tokens: result.tokens,
          deducted: result.deducted,
        },
      ]);
      if (Number.isFinite(result.remaining)) {
        await onBalanceChange?.(result.remaining);
      } else {
        await onBalanceChange?.();
      }
    } catch (err) {
      const msg =
        err.status === 402
          ? "Insufficient credits (HTTP 402)"
          : err.message || "Prompt failed";
      onNotify?.(msg, "error");
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: `Error: ${msg}`,
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="animate-rise flex min-h-[70vh] flex-col">
      <div className="mb-5">
        <h2 className="font-display text-3xl text-mist-100">
          Compute Playground
        </h2>
        <p className="mt-1 text-sm text-mist-500">
          Run prompts through the platform DeepSeek key. Credits debit after each
          completion.
        </p>
      </div>

      <div className="flex flex-1 flex-col overflow-hidden rounded-2xl border border-white/10 bg-ink-900/70 shadow-panel">
        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-6">
          {messages.length === 0 && !loading && (
            <p className="text-sm text-mist-500">
              Ask something — e.g. “Draft a SQL migration for credit top-ups.”
            </p>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`animate-rise max-w-3xl rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "ml-auto bg-signal/15 text-mist-100"
                  : m.error
                    ? "bg-warn/10 text-warn"
                    : "bg-ink-800 text-mist-100"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.role === "assistant" && !m.error && (
                <p className="mt-2 text-[11px] uppercase tracking-wider text-mist-500">
                  Consumed: {formatCredits(m.tokens)} tokens · Deducted:{" "}
                  {formatCredits(m.deducted)} credits
                </p>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-mist-500">
              <span className="inline-block h-2 w-2 animate-pulseSoft rounded-full bg-signal" />
              DeepSeek is thinking…
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form
          onSubmit={onSubmit}
          className="border-t border-white/5 bg-ink-950/60 p-4"
        >
          <div className="flex gap-3">
            <textarea
              rows={2}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Write your prompt…"
              className="min-h-[52px] flex-1 resize-none rounded-xl border border-white/10 bg-ink-900 px-3 py-3 text-sm text-mist-100 outline-none ring-signal/40 focus:ring-2"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSubmit(e);
                }
              }}
            />
            <button
              type="submit"
              disabled={loading || !prompt.trim()}
              className="self-end rounded-xl bg-signal px-5 py-3 text-sm font-semibold text-ink-950 transition hover:brightness-110 disabled:opacity-40"
            >
              Run
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
