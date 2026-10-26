"use client";

import { useMemo, useState } from "react";
import { CheckCircle2, CircleAlert, ListFilter, ReceiptText, Search, Wallet, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { Statement, Status, Summary, Transaction } from "@/lib/api";
import { formatDateTime, formatMoney } from "@/lib/format";
import { CategoryTotals } from "./CategoryTotals";
import { TransactionTable } from "./TransactionTable";
import { Card, IconCircle, Notice, STATUS_LABEL, Skeleton, type Tone, cx, fieldClass } from "./ui";

export type Tab = "all" | "needs_review" | "duplicate" | "not_spending";

const TABS: Array<{ id: Tab; label: string }> = [
  { id: "all", label: "All" },
  { id: "needs_review", label: "Needs Review" },
  { id: "duplicate", label: "Duplicates" },
  { id: "not_spending", label: "Not spending" },
];

const STATUSES: Status[] = ["auto", "learned", "user", "needs_review", "duplicate", "not_spending"];

function inTab(tx: Transaction, tab: Tab): boolean {
  if (tab === "all") return true;
  // Duplicates also wait for review, so they show up in both tabs.
  if (tab === "needs_review") return tx.needs_review;
  return tx.status === tab;
}

function StatCard({
  label,
  value,
  hint,
  icon,
  tone,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  icon: LucideIcon;
  tone: Tone;
}) {
  return (
    <Card as="div" className="flex items-start justify-between gap-3 p-4 sm:p-5">
      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-faint">{label}</p>
        <p className="mt-2 break-words text-xl font-semibold tabular-nums text-ink sm:text-[28px]">{value}</p>
        {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
      </div>
      <span className="hidden sm:inline-flex">
        <IconCircle icon={icon} tone={tone} />
      </span>
    </Card>
  );
}

export function StatCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
      {[0, 1, 2, 3].map((i) => (
        <Card as="div" key={i} className="p-5">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="mt-3 h-7 w-20" />
          <Skeleton className="mt-2 h-3 w-32" />
        </Card>
      ))}
    </div>
  );
}

export function TableSkeleton() {
  return (
    <Card className="p-5" aria-busy="true" aria-label="Loading transactions">
      <Skeleton className="h-4 w-48" />
      <div className="mt-5 space-y-4">
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="flex items-center gap-4">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 flex-1" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-20" />
          </div>
        ))}
      </div>
    </Card>
  );
}

export function StatementView({
  statement,
  summary,
  summaryError,
  categories,
  tab,
  onTabChange,
  savingId,
  saveMessage,
  saveError,
  onCategoryChange,
  exportUrl,
}: {
  statement: Statement;
  summary: Summary | null;
  summaryError: string | null;
  categories: string[];
  tab: Tab;
  onTabChange: (t: Tab) => void;
  savingId: number | null;
  saveMessage: string | null;
  saveError: string | null;
  onCategoryChange: (tx: Transaction, category: string) => void;
  exportUrl: string;
}) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [status, setStatus] = useState<Status | "">("");

  const txs = useMemo(() => statement.transactions ?? [], [statement.transactions]);

  const tabCounts = useMemo(() => {
    const counts: Record<Tab, number> = { all: txs.length, needs_review: 0, duplicate: 0, not_spending: 0 };
    for (const t of txs) {
      if (t.needs_review) counts.needs_review++;
      if (t.status === "duplicate" || t.status === "not_spending") counts[t.status]++;
    }
    return counts;
  }, [txs]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return txs.filter(
      (t) =>
        inTab(t, tab) &&
        (!category || t.category === category) &&
        (!status || t.status === status) &&
        (!q ||
          (t.normalized_merchant ?? "").toLowerCase().includes(q) ||
          (t.description ?? "").toLowerCase().includes(q)),
    );
  }, [txs, tab, category, status, query]);

  const filtersActive = query !== "" || category !== "" || status !== "";
  const clearFilters = () => {
    setQuery("");
    setCategory("");
    setStatus("");
  };

  const t = summary?.totals;
  const autoPct = t && t.transactions > 0 ? Math.round((t.auto_categorized / t.transactions) * 100) : null;

  return (
    <div className="space-y-6">
      {statement.warnings?.length ? (
        <Notice
          title={`${statement.warnings.length} ${statement.warnings.length === 1 ? "row needs" : "rows need"} your attention from the upload`}
        >
          <ul className="list-disc space-y-0.5 pl-4">
            {statement.warnings.map((w, i) => (
              <li key={`${i}-${w}`}>{w}</li>
            ))}
          </ul>
        </Notice>
      ) : null}

      {summaryError ? (
        <Notice tone="red" title="Could not load the summary">
          {summaryError}
        </Notice>
      ) : null}

      {t ? (
        <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
          <StatCard
            label="Transactions"
            value={t.transactions}
            hint={
              t.duplicates
                ? `${t.duplicates} possible ${t.duplicates === 1 ? "duplicate" : "duplicates"}`
                : `${statement.filename}`
            }
            icon={ReceiptText}
            tone="accent"
          />
          <StatCard
            label="Auto-categorized"
            value={t.auto_categorized}
            hint={autoPct !== null ? `${autoPct}% matched a rule` : undefined}
            icon={CheckCircle2}
            tone="accent"
          />
          <StatCard
            label="Needs Review"
            value={t.needs_review}
            hint={t.needs_review ? "Left out of totals until fixed" : "Nothing left to review"}
            icon={CircleAlert}
            tone="amber"
          />
          <StatCard
            label="Total spending"
            value={formatMoney(t.net_spending)}
            hint={`Net of ${formatMoney(t.refunds)} refunds`}
            icon={Wallet}
            tone="accent"
          />
        </div>
      ) : summaryError ? null : (
        <StatCardsSkeleton />
      )}

      <Card className="p-5">
        <div className="flex items-center gap-2">
          <ListFilter size={16} strokeWidth={1.75} className="text-faint" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-ink">Filter transactions</h2>
          {filtersActive ? (
            <button
              type="button"
              onClick={clearFilters}
              className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-accent hover:underline"
            >
              <X size={13} aria-hidden="true" />
              Clear filters
            </button>
          ) : null}
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)]">
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-muted">Search</span>
            <span className="relative block">
              <Search
                size={16}
                strokeWidth={1.75}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
                aria-hidden="true"
              />
              <input
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Merchant or description"
                className={cx(fieldClass, "pl-9")}
              />
            </span>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-muted">Category</span>
            <select value={category} onChange={(e) => setCategory(e.target.value)} className={fieldClass}>
              <option value="">All categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="mb-1.5 block text-xs font-medium text-muted">Status</span>
            <select value={status} onChange={(e) => setStatus(e.target.value as Status | "")} className={fieldClass}>
              <option value="">All statuses</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABEL[s]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </Card>

      <Card>
        <div className="flex flex-col gap-3 border-b border-line px-5 pt-4 sm:flex-row sm:items-end sm:justify-between">
          <div
            role="tablist"
            aria-label="Transaction views"
            className="-mb-px flex gap-1 overflow-x-auto"
            onKeyDown={(e) => {
              if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
              const i = TABS.findIndex((x) => x.id === tab);
              const next = TABS[(i + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length];
              onTabChange(next.id);
              (e.currentTarget.querySelector(`#tab-${next.id}`) as HTMLButtonElement | null)?.focus();
            }}
          >
            {TABS.map(({ id, label }) => {
              const active = id === tab;
              return (
                <button
                  key={id}
                  type="button"
                  role="tab"
                  id={`tab-${id}`}
                  aria-selected={active}
                  aria-controls="transactions-panel"
                  tabIndex={active ? 0 : -1}
                  onClick={() => onTabChange(id)}
                  className={cx(
                    "inline-flex shrink-0 items-center gap-2 border-b-2 px-3 pb-3 pt-1 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-accent",
                    active ? "border-accent font-medium text-ink" : "border-transparent text-muted hover:text-ink",
                  )}
                >
                  {label}
                  <span
                    className={cx(
                      "rounded-full px-1.5 py-px text-xs tabular-nums",
                      active ? "bg-accent-soft text-accent" : "bg-grey-soft text-muted",
                    )}
                  >
                    {tabCounts[id]}
                  </span>
                </button>
              );
            })}
          </div>
          <p className="pb-3 text-xs text-faint">
            {statement.filename} &middot; uploaded {formatDateTime(statement.uploaded_at)}
          </p>
        </div>

        <div aria-live="polite">
          {saveError ? (
            <p role="alert" className="border-b border-line bg-red-soft px-5 py-2.5 text-sm text-red">
              {saveError}
            </p>
          ) : saveMessage ? (
            <p className="border-b border-line bg-accent-soft px-5 py-2.5 text-sm text-accent">{saveMessage}</p>
          ) : null}
        </div>

        <div id="transactions-panel" role="tabpanel" aria-labelledby={`tab-${tab}`}>
          {rows.length ? (
            <TransactionTable
              rows={rows}
              categories={categories}
              savingId={savingId}
              onCategoryChange={onCategoryChange}
            />
          ) : (
            <div className="flex flex-col items-center px-6 py-14 text-center">
              <IconCircle icon={tab === "needs_review" && !filtersActive ? CheckCircle2 : Search} tone="grey" />
              <p className="mt-3 text-sm font-medium text-ink">
                {filtersActive
                  ? "No transactions match these filters"
                  : tab === "needs_review"
                    ? "Nothing needs review. Every row has a category."
                    : tab === "all"
                      ? "This statement has no transactions"
                      : `No ${TABS.find((x) => x.id === tab)?.label.toLowerCase()} rows in this statement`}
              </p>
              {filtersActive ? (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="mt-2 text-sm font-medium text-accent hover:underline"
                >
                  Clear filters
                </button>
              ) : null}
            </div>
          )}
        </div>
      </Card>

      {summary ? <CategoryTotals summary={summary} exportUrl={exportUrl} /> : null}
    </div>
  );
}
