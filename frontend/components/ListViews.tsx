"use client";

import { useCallback, useEffect, useState } from "react";
import { BookOpenCheck, ChevronRight, FileSpreadsheet, Loader2, RotateCw, Trash2 } from "lucide-react";
import { api, errorMessage, type LearnedRule } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { Card, IconCircle, Notice, Skeleton, buttonSecondary, cx } from "./ui";

type Load<T> = { status: "loading" } | { status: "error"; message: string } | { status: "ready"; data: T };

function useLoad<T>(fetcher: () => Promise<T>) {
  const [state, setState] = useState<Load<T>>({ status: "loading" });
  const reload = useCallback(() => {
    setState({ status: "loading" });
    fetcher()
      .then((data) => setState({ status: "ready", data }))
      .catch((err) => setState({ status: "error", message: errorMessage(err) }));
  }, [fetcher]);
  useEffect(() => {
    reload();
  }, [reload]);
  return [state, reload, setState] as const;
}

function ListSkeleton() {
  return (
    <div className="space-y-4 p-5" aria-busy="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="flex items-center gap-4">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-24" />
        </div>
      ))}
    </div>
  );
}

function RetryNotice({ title, message, onRetry }: { title: string; message: string; onRetry: () => void }) {
  return (
    <div className="p-5">
      <Notice
        tone="red"
        title={title}
        action={
          <button type="button" onClick={onRetry} className={cx(buttonSecondary, "h-8 px-3 text-xs")}>
            <RotateCw size={14} aria-hidden="true" />
            Retry
          </button>
        }
      >
        {message}
      </Notice>
    </div>
  );
}

const headCell = "py-3 pr-4 text-[11px] font-semibold uppercase tracking-wider text-faint";

export function StatementsList({ activeId, onOpen }: { activeId: number | null; onOpen: (id: number) => void }) {
  const [state, reload] = useLoad(api.listStatements);

  return (
    <Card>
      <div className="border-b border-line px-5 py-4">
        <h2 className="text-base font-semibold text-ink">Uploaded statements</h2>
        <p className="text-xs text-muted">Newest first. Open one to review its transactions.</p>
      </div>
      {state.status === "loading" ? (
        <ListSkeleton />
      ) : state.status === "error" ? (
        <RetryNotice title="Could not load statements" message={state.message} onRetry={reload} />
      ) : state.data.length === 0 ? (
        <div className="flex flex-col items-center px-6 py-14 text-center">
          <IconCircle icon={FileSpreadsheet} tone="grey" />
          <p className="mt-3 text-sm font-medium text-ink">No statements yet</p>
          <p className="mt-1 text-sm text-muted">Upload a CSV or try the sample statement from the Dashboard.</p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px] text-left text-sm">
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className={cx(headCell, "pl-5")}>
                  File
                </th>
                <th scope="col" className={headCell}>
                  Uploaded
                </th>
                <th scope="col" className={cx(headCell, "text-right")}>
                  Rows
                </th>
                <th scope="col" className={headCell}>
                  Review
                </th>
                <th scope="col" className="w-10 pr-5">
                  <span className="sr-only">Open</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {state.data.map((s) => (
                <tr
                  key={s.id}
                  onClick={() => onOpen(s.id)}
                  className={cx(
                    "cursor-pointer border-b border-line last:border-b-0 hover:bg-page",
                    s.id === activeId && "bg-accent-soft/50",
                  )}
                >
                  <td className="py-3.5 pl-5 pr-4">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onOpen(s.id);
                      }}
                      className="flex items-center gap-3 text-left font-semibold text-ink hover:text-accent focus-visible:outline-2 focus-visible:outline-accent"
                    >
                      <IconCircle icon={FileSpreadsheet} size="sm" />
                      <span className="break-all">{s.filename}</span>
                    </button>
                  </td>
                  <td className="py-3.5 pr-4 whitespace-nowrap text-muted">{formatDateTime(s.uploaded_at)}</td>
                  <td className="py-3.5 pr-4 text-right tabular-nums text-ink">{s.row_count}</td>
                  <td className="py-3.5 pr-4">
                    {s.needs_review_count > 0 ? (
                      <span className="rounded-full bg-amber-soft px-2 py-0.5 text-xs font-medium tabular-nums text-amber">
                        {s.needs_review_count} to review
                      </span>
                    ) : (
                      <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-medium text-accent">
                        All done
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 pr-5 text-faint">
                    <ChevronRight size={16} aria-hidden="true" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

export function LearnedRules() {
  const [state, reload, setState] = useLoad(api.listRules);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const remove = async (rule: LearnedRule) => {
    setDeleting(rule.id);
    setDeleteError(null);
    try {
      await api.deleteRule(rule.id);
      setState((s) => (s.status === "ready" ? { status: "ready", data: s.data.filter((r) => r.id !== rule.id) } : s));
    } catch (err) {
      setDeleteError(`Could not delete the rule for ${rule.merchant}: ${errorMessage(err)}`);
    } finally {
      setDeleting(null);
    }
  };

  return (
    <Card>
      <div className="border-b border-line px-5 py-4">
        <h2 className="text-base font-semibold text-ink">Merchant rules</h2>
        <p className="text-xs text-muted">
          Created when you change a category. Future uploads use them before the built-in rules.
        </p>
      </div>
      {deleteError ? (
        <p role="alert" className="border-b border-line bg-red-soft px-5 py-2.5 text-sm text-red">
          {deleteError}
        </p>
      ) : null}
      {state.status === "loading" ? (
        <ListSkeleton />
      ) : state.status === "error" ? (
        <RetryNotice title="Could not load learned rules" message={state.message} onRetry={reload} />
      ) : state.data.length === 0 ? (
        <div className="flex flex-col items-center px-6 py-14 text-center">
          <IconCircle icon={BookOpenCheck} tone="grey" />
          <p className="mt-3 text-sm font-medium text-ink">No learned rules yet</p>
          <p className="mt-1 max-w-sm text-sm text-muted">
            Pick a category for a transaction and LedgerLite will remember that merchant next time.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[620px] text-left text-sm">
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className={cx(headCell, "pl-5")}>
                  Merchant
                </th>
                <th scope="col" className={headCell}>
                  Category
                </th>
                <th scope="col" className={cx(headCell, "text-right")}>
                  Times applied
                </th>
                <th scope="col" className={headCell}>
                  Created
                </th>
                <th scope="col" className="w-24 pr-5">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {state.data.map((r) => (
                <tr key={r.id} className="border-b border-line last:border-b-0">
                  <td className="py-3.5 pl-5 pr-4 font-semibold text-ink">{r.merchant}</td>
                  <td className="py-3.5 pr-4">
                    <span className="rounded-full bg-blue-soft px-2 py-0.5 text-xs font-medium text-blue">
                      {r.category}
                    </span>
                  </td>
                  <td className="py-3.5 pr-4 text-right tabular-nums text-ink">{r.times_applied}</td>
                  <td className="py-3.5 pr-4 whitespace-nowrap text-muted">{formatDateTime(r.created_at)}</td>
                  <td className="py-2.5 pr-5 text-right">
                    <button
                      type="button"
                      onClick={() => remove(r)}
                      disabled={deleting === r.id}
                      aria-label={`Delete rule for ${r.merchant}`}
                      className="inline-flex h-9 items-center gap-1.5 rounded-lg px-2.5 text-sm text-muted transition-colors hover:bg-red-soft hover:text-red disabled:opacity-60"
                    >
                      {deleting === r.id ? (
                        <Loader2 size={15} className="animate-spin" aria-hidden="true" />
                      ) : (
                        <Trash2 size={15} strokeWidth={1.75} aria-hidden="true" />
                      )}
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
