"use client";
import type { CategoryCode } from "@/lib/api/types";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { DecisionPanel, type Draft } from "./DecisionPanel";
import { HelpSheet } from "./HelpSheet";
import { Toast, type ToastState } from "./Toast";
import { TopBar } from "./TopBar";
import { TransactionList } from "./TransactionList";
import { rankedCategories } from "./CategorySelect";
import { api } from "@/lib/api/client";
import {
  useCategories,
  useFixTransaction,
  useRestoreDuplicate,
  TX_PAGE,
  usePagedTransactions,
  useStatement,
  useSummary,
} from "@/lib/api/hooks";
import type { TransactionOut } from "@/lib/api/types";
import { categoryLabel, merchantName } from "@/lib/categories";
import { period } from "@/lib/format";

type Tab = "review" | "all" | "excluded" | "dups";

export function ReviewWorkspace({ id }: { id: string }) {
  const st = useStatement(id);
  const [pages, setPages] = useState(1);
  const txq = usePagedTransactions(id, pages);
  const cats = useCategories();
  const summary = useSummary(id);
  const fix = useFixTransaction(id);
  const restore = useRestoreDuplicate(id);

  const [tab, setTab] = useState<Tab | null>(null);
  const [q, setQ] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftState, setDraftState] = useState<(Draft & { id: string }) | null>(null);
  const [toast, setToast] = useState<ToastState | null>(null);
  const [help, setHelp] = useState(false);
  const [leaving, setLeaving] = useState<Map<string, TransactionOut>>(new Map());
  const undoRef = useRef<(() => void) | null>(null);
  const [initialNeed, setInitialNeed] = useState(0);
  // The API cannot unconfirm a row (any fix marks it user_confirmed), so an undone row is kept
  // "reopened" on the client: it shows as Needs your review until the user confirms it again.
  const [reopened, setReopened] = useState<Map<string, TransactionOut>>(new Map());
  const panelRef = useRef<HTMLElement>(null);
  const refocusPanel = useRef(false);

  const items = useMemo(
    () => (txq.data?.items ?? []).map((t) => (t.status === "user_confirmed" ? (reopened.get(t.id) ?? t) : t)),
    [txq.data, reopened],
  );
  const kindOf = useCallback(
    (code: string | null) => cats.data?.find((c) => c.code === code)?.kind,
    [cats.data],
  );

  const need = items.filter((t) => t.status === "needs_review").length;
  if (need > initialNeed) setInitialNeed(need);
  const dupCount = items.filter((t) => t.status === "duplicate").length;
  const excludedCount = items.filter((t) => t.status !== "duplicate" && kindOf(t.category) === "non_pnl").length;
  const allCount = items.filter((t) => t.status !== "duplicate").length;

  const activeTab: Tab = tab ?? (txq.data ? (need > 0 ? "review" : "all") : "review");

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const base = items.filter((t) => {
      if (needle && !t.description.toLowerCase().includes(needle)) return false;
      if (activeTab === "review") return t.status === "needs_review";
      if (activeTab === "dups") return t.status === "duplicate";
      if (t.status === "duplicate") return false;
      if (activeTab === "excluded") return kindOf(t.category) === "non_pnl";
      return true;
    });
    const ids = new Set(base.map((t) => t.id));
    const extra = [...leaving.values()].filter((t) => !ids.has(t.id));
    return [...base, ...extra].sort((a, b) => a.row_index - b.row_index);
  }, [items, activeTab, q, leaving, kindOf]);

  const live = visible.filter((t) => !leaving.has(t.id));
  const sel = live.find((t) => t.id === selectedId) ?? live[0] ?? null;
  const similarRows = useMemo(
    () =>
      sel
        ? items.filter((t) => t.id !== sel.id && t.merchant_key === sel.merchant_key && t.status !== "user_confirmed" && t.status !== "duplicate")
        : [],
    [items, sel],
  );

  // After Confirm the panel remounts for the next row; put focus on its heading so keyboard and
  // screen reader users keep their place (the heading is read out as the new row).
  const selKey = sel?.id ?? null;
  useEffect(() => {
    if (!refocusPanel.current) return;
    refocusPanel.current = false;
    const target = panelRef.current?.querySelector<HTMLElement>("[data-decision-heading]") ?? panelRef.current;
    target?.focus();
  }, [selKey]);

  const defaults = (t: TransactionOut): Draft => ({
    category: t.category ?? t.brain_category ?? "",
    remember: false,
    similar: false,
  });
  const draft: Draft = sel ? (draftState?.id === sel.id ? draftState : defaults(sel)) : { category: "", remember: false, similar: false };
  const patchDraft = (p: Partial<Draft>) => sel && setDraftState({ ...draft, ...p, id: sel.id });

  const move = useCallback(
    (delta: number) => {
      if (live.length === 0) return;
      const i = Math.max(0, live.findIndex((t) => t.id === sel?.id));
      const next = live[Math.min(live.length - 1, Math.max(0, i + delta))];
      if (next) setSelectedId(next.id);
    },
    [live, sel],
  );

  const confirm = useCallback(() => {
    if (!sel || !draft.category || fix.isPending) return;
    const target = sel;
    const affected = items.filter(
      (t) => t.id === target.id || (draft.similar && t.merchant_key === target.merchant_key && t.status !== "user_confirmed"),
    );
    const prior = new Map(affected.map((t) => [t.id, t] as const));
    setReopened((m) => {
      const n = new Map(m);
      affected.forEach((t) => n.delete(t.id));
      return n;
    });
    if (panelRef.current?.contains(document.activeElement) || document.activeElement === document.body) refocusPanel.current = true;
    const nextIdx = live.findIndex((t) => t.id === target.id) + 1;
    const nextRow = live[nextIdx] ?? live[nextIdx - 2];
    if (activeTab === "review") {
      setLeaving((m) => new Map(m).set(target.id, target));
      setTimeout(
        () =>
          setLeaving((m) => {
            const n = new Map(m);
            n.delete(target.id);
            return n;
          }),
        300,
      );
    }
    if (nextRow) setSelectedId(nextRow.id);
    const label = categoryLabel(cats.data, draft.category);
    fix.mutate(
      { id: target.id, category: draft.category as CategoryCode, remember: draft.remember, apply_to_similar: draft.similar },
      {
        onSuccess: (res) => {
          const undo = async () => {
            const reopen = new Map<string, TransactionOut>();
            for (const row of res.updated) {
              const was = prior.get(row.id);
              if (!was) continue;
              const cat = was.category ?? was.brain_category;
              if (cat) await api.fix(row.id, { category: cat });
              if (was.status !== "user_confirmed") reopen.set(row.id, was);
            }
            setReopened((m) => new Map([...m, ...reopen]));
            setTab("review");
            setSelectedId(target.id);
            await Promise.all([txq.refetch(), summary.refetch(), st.refetch()]);
            setToast({ id: Date.now(), message: "Change undone. The row is back in Needs your review." });
          };
          undoRef.current = () => void undo();
          const n = res.updated.length;
          setToast({
            id: Date.now(),
            message: `Confirmed ${merchantName(target)} as ${label}${n > 1 ? ` (${n} rows)` : ""}.`,
            undo: () => void undo(),
          });
        },
        onError: (e) => setToast({ id: Date.now(), message: e.message, error: true }),
      },
    );
  }, [sel, draft, fix, items, live, activeTab, cats.data, txq, summary, st]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const el = e.target as HTMLElement;
      if (el.closest("input, textarea, select, [role=dialog]")) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      const k = e.key;
      if (k === "j" || k === "J") move(1);
      else if (k === "k" || k === "K") move(-1);
      else if (k === "?") setHelp(true);
      else if (k === "r" || k === "R") patchDraft({ remember: !draft.remember });
      else if (k === "u" || k === "U") undoRef.current?.();
      else if (k === "Enter" && !el.closest("button, a")) {
        e.preventDefault();
        confirm();
      } else if (/^[1-9]$/.test(k) && sel && cats.data) {
        const pick = rankedCategories(cats.data, sel.direction, sel.is_refund, sel.category ?? sel.brain_category)[Number(k) - 1];
        if (pick) patchDraft({ category: pick.code });
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const total = summary.data?.schedule_e.find((l) => l.category === draft.category)?.total_cents;
  const dismiss = useCallback(() => setToast(null), []);

  if (st.isError)
    return (
      <>
        <TopBar step={2} />
        <main className="mx-auto max-w-3xl px-4 py-10">
          <p role="alert" className="text-error">{st.error.message}</p>
          <Link href="/" className="text-ledger underline">Back to upload</Link>
        </main>
      </>
    );

  const s = st.data;
  const tabs: [Tab, string, number][] = [
    ["review", "Needs your review", need],
    ["all", "All", allCount],
    ["excluded", "Not counted", excludedCount],
    ["dups", "Duplicates", dupCount],
  ];

  return (
    <>
      <TopBar
        step={2}
        statementId={id}
        title={s ? `${s.filename} (${period(s.period_start, s.period_end)})` : "Loading statement..."}
      />
      <main className="mx-auto max-w-6xl">
        {s && s.warnings.length > 0 && (
          <details className="mx-4 mt-3 border-l-4 border-attention bg-attention-fill px-3 py-2 text-attention">
            <summary className="cursor-pointer font-medium">{s.warnings.length} things to check in this file</summary>
            <ul className="mt-1 list-disc pl-5 text-ink">
              {s.warnings.map((w, i) => (
                <li key={i}>{w.row_index != null ? `Row ${w.row_index}: ` : ""}{w.message}</li>
              ))}
            </ul>
          </details>
        )}
        <div className="flex flex-wrap items-end gap-x-4 gap-y-2 border-b border-rule px-4 pt-3">
          <div role="tablist" aria-label="Filter transactions" className="flex flex-wrap gap-x-5">
            {tabs.map(([key, label, n]) => (
              <button
                key={key}
                role="tab"
                type="button"
                aria-selected={activeTab === key}
                onClick={() => setTab(key)}
                className={`border-b-2 pb-2 ${activeTab === key ? "border-ledger font-medium text-ink" : "border-transparent text-muted"}`}
              >
                {label} <span className="num">{n}</span>
              </button>
            ))}
          </div>
          <div className="ml-auto pb-2">
            <label htmlFor="search" className="sr-only">Search descriptions</label>
            <input
              id="search"
              type="search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search"
              className="rounded-xs border border-muted bg-row px-2 py-1"
            />
          </div>
        </div>

        <div className="review-grid">
          <div className="min-w-0">
            {txq.isLoading && <p className="p-4 text-muted">Loading transactions...</p>}
            {txq.isError && (
              <p role="alert" className="p-4 text-error">
                {txq.error?.message}{" "}
                <button type="button" className="underline" onClick={() => void txq.refetch()}>Try again</button>
              </p>
            )}
            {txq.data && visible.length === 0 && (
              <div className="p-6">
                {activeTab === "review" && !q ? (
                  <>
                    <p className="text-lg font-medium">All rows reviewed. Your Schedule E is ready to export.</p>
                    <p className="mt-3 flex gap-6">
                      <Link href={`/statements/${id}/summary`} className="font-medium text-ledger underline">View Schedule E</Link>
                      <a href={api.exportUrl(id)} className="font-medium text-ledger underline">Export CSV</a>
                    </p>
                  </>
                ) : (
                  <p className="text-muted">No transactions here. Try another tab or clear the search.</p>
                )}
              </div>
            )}
            {visible.length > 0 && (
              <TransactionList
                items={visible}
                selectedId={sel?.id ?? null}
                leavingIds={new Set(leaving.keys())}
                categories={cats.data}
                showCategory={activeTab !== "review"}
                onSelect={setSelectedId}
              />
            )}
            {txq.data && txq.data.total > txq.data.items.length && (
              <p className="px-4 py-3 text-sm text-muted">
                Showing {txq.data.items.length} of {txq.data.total}.{" "}
                <button
                  type="button"
                  className="text-ledger underline"
                  disabled={txq.isFetching}
                  onClick={() => setPages((p) => p + 1)}
                >
                  Show {Math.min(TX_PAGE, txq.data.total - txq.data.items.length)} more
                </button>
              </p>
            )}
            <div className="flex items-center gap-3 px-4 py-3 text-sm text-muted">
              <span>{need} of {Math.max(initialNeed, need)} left</span>
              <progress
                aria-label="Review progress"
                className="h-2 w-40 accent-ledger"
                value={Math.max(initialNeed, need) - need}
                max={Math.max(1, initialNeed)}
              />
              <button type="button" onClick={() => setHelp(true)} className="ml-auto underline">Shortcuts</button>
              <Link href={`/statements/${id}/summary`} className="underline">Schedule E summary</Link>
            </div>
          </div>

          <aside ref={panelRef} tabIndex={-1} className="decision-panel panel-shadow border-l border-rule bg-row outline-offset-[-2px]" aria-label="Decision panel">
            {sel && cats.data ? (
              <DecisionPanel
                key={sel.id}
                tx={sel}
                categories={cats.data}
                draft={draft}
                onDraft={patchDraft}
                onConfirm={confirm}
                onSkip={() => move(1)}
                onRestore={() => restore.mutate(sel.id)}
                busy={fix.isPending}
                totalSoFar={total}
                similarRows={similarRows}
              />
            ) : (
              <p className="p-4 text-muted">Select a transaction to see why it was sorted this way.</p>
            )}
          </aside>
        </div>
      </main>
      <HelpSheet open={help} onOpenChange={setHelp} />
      <Toast toast={toast} onDismiss={dismiss} />
    </>
  );
}
