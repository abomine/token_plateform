"use client";

import { useState } from "react";
import { buyCredits, formatCredits } from "@/lib/api";

const PACKS = [
  { label: "Starter", amount: 100_000, usd: 0.1 },
  { label: "Growth", amount: 1_000_000, usd: 1 },
  { label: "Scale", amount: 5_000_000, usd: 5 },
];

export default function TopupModal({ open, onClose, onSuccess, onNotify }) {
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState(PACKS[1].amount);

  if (!open) return null;

  async function confirm() {
    setBusy(true);
    try {
      const result = await buyCredits(selected);
      onNotify?.(
        `Stripe simulation OK · +${formatCredits(result.added)} credits`,
        "ok"
      );
      onSuccess?.(result.credit_balance);
      onClose?.();
    } catch (err) {
      onNotify?.(err.message || "Top-up failed", "error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="animate-rise w-full max-w-md rounded-2xl border border-white/10 bg-ink-900 p-6 shadow-panel">
        <div className="mb-5 flex items-start justify-between gap-3">
          <div>
            <h3 className="font-display text-2xl text-mist-100">
              Recharger Credits
            </h3>
            <p className="mt-1 text-sm text-mist-500">
              Simulated Stripe Checkout — no real payment in Phase 1.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-mist-500 hover:text-mist-100"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="space-y-2">
          {PACKS.map((pack) => (
            <button
              key={pack.amount}
              type="button"
              onClick={() => setSelected(pack.amount)}
              className={`flex w-full items-center justify-between rounded-xl border px-4 py-3 text-left transition ${
                selected === pack.amount
                  ? "border-signal/50 bg-signal/10"
                  : "border-white/10 bg-ink-950 hover:border-white/20"
              }`}
            >
              <span>
                <span className="block text-sm font-medium text-mist-100">
                  {pack.label}
                </span>
                <span className="text-xs text-mist-500">
                  {formatCredits(pack.amount)} credits
                </span>
              </span>
              <span className="font-display text-lg text-signal">
                ${pack.usd}
              </span>
            </button>
          ))}
        </div>

        <button
          type="button"
          disabled={busy}
          onClick={confirm}
          className="mt-5 w-full rounded-xl bg-signal py-3 text-sm font-semibold text-ink-950 disabled:opacity-50"
        >
          {busy ? "Processing…" : "Payer avec Stripe (simulé)"}
        </button>
      </div>
    </div>
  );
}
