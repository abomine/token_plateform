"use client";

import { useCallback, useEffect, useState } from "react";
import Header from "@/components/Header";
import TaskMarketplace from "@/components/TaskMarketplace";
import Playground from "@/components/Playground";
import TopupModal from "@/components/TopupModal";
import { fetchBalance } from "@/lib/api";

const TABS = [
  { id: "tasks", label: "Micro-Tasks" },
  { id: "playground", label: "Compute Playground" },
];

export default function HomePage() {
  const [tab, setTab] = useState("tasks");
  const [balance, setBalance] = useState(null);
  const [balanceLoading, setBalanceLoading] = useState(true);
  const [balanceAnimating, setBalanceAnimating] = useState(false);
  const [topupOpen, setTopupOpen] = useState(false);
  const [toast, setToast] = useState(null);

  const notify = useCallback((message, tone = "ok") => {
    setToast({ message, tone });
    window.setTimeout(() => setToast(null), 4200);
  }, []);

  const refreshBalance = useCallback(
    async (nextValue) => {
      if (typeof nextValue === "number") {
        setBalance(nextValue);
        setBalanceAnimating(true);
        window.setTimeout(() => setBalanceAnimating(false), 600);
        return;
      }
      setBalanceLoading(true);
      try {
        const data = await fetchBalance();
        setBalance(data.credit_balance);
        setBalanceAnimating(true);
        window.setTimeout(() => setBalanceAnimating(false), 600);
      } catch (err) {
        notify(err.message || "Could not load balance", "error");
      } finally {
        setBalanceLoading(false);
      }
    },
    [notify]
  );

  useEffect(() => {
    refreshBalance();
  }, [refreshBalance]);

  return (
    <div className="min-h-screen">
      <Header
        balance={balance}
        balanceAnimating={balanceAnimating}
        loading={balanceLoading}
        onRecharge={() => setTopupOpen(true)}
      />

      <main className="mx-auto max-w-6xl px-5 pb-16 pt-8">
        <div className="mb-8 flex gap-2 rounded-2xl border border-white/8 bg-ink-900/60 p-1.5">
          {TABS.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setTab(item.id)}
              className={`flex-1 rounded-xl px-4 py-2.5 text-sm font-medium transition ${
                tab === item.id
                  ? "bg-ink-700 text-mist-100 shadow-panel"
                  : "text-mist-500 hover:text-mist-100"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>

        {tab === "tasks" ? (
          <TaskMarketplace
            onBalanceChange={refreshBalance}
            onNotify={notify}
          />
        ) : (
          <Playground onBalanceChange={refreshBalance} onNotify={notify} />
        )}
      </main>

      <TopupModal
        open={topupOpen}
        onClose={() => setTopupOpen(false)}
        onSuccess={(next) => refreshBalance(next)}
        onNotify={notify}
      />

      {toast && (
        <div
          className={`fixed bottom-5 right-5 z-50 max-w-sm animate-rise rounded-xl border px-4 py-3 text-sm shadow-panel ${
            toast.tone === "error"
              ? "border-warn/40 bg-ink-900 text-warn"
              : "border-signal/40 bg-ink-900 text-signal"
          }`}
        >
          {toast.message}
        </div>
      )}
    </div>
  );
}
