"use client";

import { useEffect, useState } from "react";
import { CategoryTotals } from "@/components/categorize/CategoryTotals";
import { SummaryCards } from "@/components/categorize/SummaryCards";
import { TransactionsTable } from "@/components/categorize/TransactionsTable";
import { UploadPanel } from "@/components/categorize/UploadPanel";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { exportUrl, fixTransaction, getCategories, getStatement, uploadStatement } from "@/lib/api";
import type { Category, StatementResult } from "@/lib/types";

function setUrl(statementId: number | null) {
  const url = new URL(window.location.href);
  if (statementId) url.searchParams.set("statement", String(statementId));
  else {
    url.searchParams.delete("statement");
    url.searchParams.delete("view");
  }
  window.history.replaceState(null, "", url);
}

export default function CategorizePage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [result, setResult] = useState<StatementResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCategories().then(setCategories).catch((e: Error) => setError(e.message));
    // Reopen the statement in the address bar, so a refresh keeps your place.
    const id = Number(new URLSearchParams(window.location.search).get("statement"));
    if (id) {
      setBusy(true);
      getStatement(id)
        .then(setResult)
        .catch(() => setUrl(null))
        .finally(() => setBusy(false));
    }
  }, []);

  const show = (data: StatementResult | null) => {
    setResult(data);
    setUrl(data?.statement.id ?? null);
  };

  const upload = async (file: File, sign: "auto" | "bank" | "card") => {
    setBusy(true);
    setError(null);
    try {
      show(await uploadStatement(file, sign));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const fix = async (id: number, category: string, applyToSimilar: boolean) => {
    try {
      setResult(await fixTransaction(id, category, applyToSimilar));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <div className="bg-gradient-to-b from-brand-50/70 to-white">
      <div className="container-page py-10 sm:py-14">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-brand-900">Sort a statement</h1>
            <p className="mt-2 text-slate-600">
              {result
                ? "Review the rows the app was not sure about, then export."
                : "Upload a CSV and every transaction gets a category, a reason and a confidence score."}
            </p>
          </div>
          {result && (
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => show(null)}>
                Upload another
              </Button>
              <a
                href={exportUrl(result.statement.id)}
                className="inline-flex items-center rounded-lg bg-brand-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-brand-700"
              >
                Export CSV
              </a>
            </div>
          )}
        </div>

        <div className="mt-8">
          {!result ? (
            <UploadPanel busy={busy} error={error} onUpload={upload} />
          ) : (
            <div className="space-y-6">
              <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600">
                <span className="font-medium text-brand-900">{result.statement.filename}</span>
                <Badge tone="blue">{result.statement.sign_mode === "card" ? "Card layout" : "Bank layout"}</Badge>
                <span>{result.summary.transactions} transactions</span>
                {result.statement.skipped.length > 0 && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-amber-700">{result.statement.skipped.length} lines skipped</summary>
                    <ul className="mt-2 space-y-1">
                      {result.statement.skipped.map((s) => (
                        <li key={s.row}>
                          Line {s.row}: {s.reason}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
              {error && (
                <p role="alert" className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
                  {error}
                </p>
              )}
              <SummaryCards summary={result.summary} />
              <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
                <TransactionsTable transactions={result.transactions} categories={categories} onFix={fix} />
                <CategoryTotals totals={result.summary.by_category} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
