"use client";

import { useEffect, useState } from "react";
import TaskCard from "@/components/TaskCard";
import { createTask, fetchTasks, respondTask } from "@/lib/api";

const EMPTY_FORM = {
  title: "",
  description: "",
  reward_credits: 25000,
  category: "Prompting",
};

export default function TaskMarketplace({ onBalanceChange, onNotify }) {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const data = await fetchTasks();
      setTasks(data);
    } catch (err) {
      onNotify?.(err.message || "Failed to load tasks", "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRespond(task) {
    setBusyId(task.id);
    try {
      await respondTask(task.id);
      onNotify?.(`Mission completed · +${task.reward_credits} credits`, "ok");
      await load();
      await onBalanceChange?.();
    } catch (err) {
      onNotify?.(err.message || "Could not complete task", "error");
    } finally {
      setBusyId(null);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setSubmitting(true);
    try {
      await createTask({
        ...form,
        reward_credits: Number(form.reward_credits),
      });
      setForm(EMPTY_FORM);
      setShowForm(false);
      onNotify?.("Mission published", "ok");
      await load();
    } catch (err) {
      onNotify?.(err.message || "Could not create task", "error");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="animate-rise space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-3xl text-mist-100">
            Micro-Tasks Marketplace
          </h2>
          <p className="mt-1 max-w-xl text-sm text-mist-500">
            Earn credits on short B2B missions — scraping, prompting, bug fixes.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm((v) => !v)}
          className="rounded-xl border border-white/15 bg-ink-800 px-4 py-2 text-sm text-mist-100 transition hover:border-signal/40"
        >
          {showForm ? "Fermer" : "Poster une mission"}
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleCreate}
          className="grid gap-3 rounded-2xl border border-white/10 bg-ink-900 p-5 shadow-panel sm:grid-cols-2"
        >
          <label className="sm:col-span-2">
            <span className="mb-1 block text-xs uppercase tracking-wider text-mist-500">
              Title
            </span>
            <input
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full rounded-xl border border-white/10 bg-ink-950 px-3 py-2 text-mist-100 outline-none ring-signal/40 focus:ring-2"
            />
          </label>
          <label className="sm:col-span-2">
            <span className="mb-1 block text-xs uppercase tracking-wider text-mist-500">
              Description
            </span>
            <textarea
              required
              rows={3}
              value={form.description}
              onChange={(e) =>
                setForm({ ...form, description: e.target.value })
              }
              className="w-full rounded-xl border border-white/10 bg-ink-950 px-3 py-2 text-mist-100 outline-none ring-signal/40 focus:ring-2"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs uppercase tracking-wider text-mist-500">
              Credit bounty
            </span>
            <input
              type="number"
              min={1}
              required
              value={form.reward_credits}
              onChange={(e) =>
                setForm({ ...form, reward_credits: e.target.value })
              }
              className="w-full rounded-xl border border-white/10 bg-ink-950 px-3 py-2 text-mist-100 outline-none ring-signal/40 focus:ring-2"
            />
          </label>
          <label>
            <span className="mb-1 block text-xs uppercase tracking-wider text-mist-500">
              Category
            </span>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="w-full rounded-xl border border-white/10 bg-ink-950 px-3 py-2 text-mist-100 outline-none ring-signal/40 focus:ring-2"
            >
              <option>Scraping</option>
              <option>Prompting</option>
              <option>Bug Fix</option>
            </select>
          </label>
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-xl bg-signal px-4 py-2 text-sm font-semibold text-ink-950 disabled:opacity-50"
            >
              {submitting ? "Publication…" : "Publier la mission"}
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="animate-pulseSoft text-mist-500">Chargement des missions…</p>
      ) : tasks.length === 0 ? (
        <p className="text-mist-500">Aucune mission ouverte pour le moment.</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              busy={busyId === task.id}
              onRespond={handleRespond}
            />
          ))}
        </div>
      )}
    </section>
  );
}
