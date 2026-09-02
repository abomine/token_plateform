"use client";

import { formatCredits } from "@/lib/api";

const CATEGORY_STYLES = {
  Scraping: "border-sky-400/30 bg-sky-400/10 text-sky-200",
  Prompting: "border-signal/30 bg-signal/10 text-signal",
  "Bug Fix": "border-warn/30 bg-warn/10 text-warn",
};

export default function TaskCard({ task, busy, onRespond }) {
  return (
    <article className="animate-rise rounded-2xl border border-white/8 bg-ink-900/80 p-5 shadow-panel transition hover:border-signal/25">
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <span
          className={`rounded-md border px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider ${
            CATEGORY_STYLES[task.category] ||
            "border-white/10 bg-white/5 text-mist-300"
          }`}
        >
          {task.category}
        </span>
        <span className="text-xs text-mist-500">
          +{formatCredits(task.reward_credits)} credits
        </span>
      </div>
      <h3 className="font-display text-xl text-mist-100">{task.title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-mist-300">
        {task.description}
      </p>
      <button
        type="button"
        disabled={busy || task.status !== "open"}
        onClick={() => onRespond(task)}
        className="mt-4 rounded-xl border border-signal/40 bg-signal/10 px-4 py-2 text-sm font-medium text-signal transition hover:bg-signal/20 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {busy ? "Validation…" : "Répondre à la mission"}
      </button>
    </article>
  );
}
