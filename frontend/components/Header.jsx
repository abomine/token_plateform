"use client";

import { formatCredits } from "@/lib/api";

export default function Header({
  balance,
  balanceAnimating,
  onRecharge,
  loading,
}) {
  return (
    <header className="sticky top-0 z-40 border-b border-white/5 bg-ink-950/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-4">
        <div className="min-w-0">
          <p className="font-display text-2xl tracking-tight text-mist-100 sm:text-3xl">
            ComputeMarket
            <span className="ml-2 align-middle text-sm font-sans font-medium tracking-[0.18em] text-signal">
              B2B
            </span>
          </p>
          <p className="mt-0.5 hidden text-sm text-mist-500 sm:block">
            Credits for compute & micro-missions
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div
            className={`rounded-xl border border-white/10 bg-ink-900 px-4 py-2 text-right ${
              balanceAnimating ? "animate-balancePop" : ""
            }`}
          >
            <p className="text-[10px] uppercase tracking-[0.2em] text-mist-500">
              Balance
            </p>
            <p className="font-display text-lg text-mist-100 tabular-nums sm:text-xl">
              {loading && balance == null ? (
                <span className="animate-pulseSoft">…</span>
              ) : (
                <>
                  {formatCredits(balance ?? 0)}
                  <span className="ml-1 text-xs font-sans text-mist-500">
                    Credits
                  </span>
                </>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={onRecharge}
            className="rounded-xl bg-signal px-4 py-2.5 text-sm font-semibold text-ink-950 transition hover:brightness-110 active:scale-[0.98]"
          >
            Recharger +
          </button>
        </div>
      </div>
    </header>
  );
}
