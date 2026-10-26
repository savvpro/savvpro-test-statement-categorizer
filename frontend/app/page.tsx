"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getCategories,
  getSummary,
  getTransactions,
  updateCategory,
  uploadCsv,
  type Summary,
  type Transaction,
} from "@/lib/api";
import { applyFilters, type Tab } from "@/lib/format";
import { CategoryBars } from "@/components/CategoryBars";
import { FilterBar } from "@/components/FilterBar";
import { SummaryCards } from "@/components/SummaryCards";
import { TransactionsTable } from "@/components/TransactionsTable";
import { UploadZone } from "@/components/UploadZone";

const errorText = (e: unknown) => (e instanceof Error ? e.message : "Something went wrong.");

export default function Home() {
  const [rows, setRows] = useState<Transaction[] | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [tab, setTab] = useState<Tab>("all");
  const [category, setCategory] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [fileName, setFileName] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [skipped, setSkipped] = useState<string[]>([]);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({});

  const refreshSummary = useCallback(async () => {
    try {
      setSummary(await getSummary());
    } catch (e) {
      setUploadError(errorText(e));
    }
  }, []);

  // On load: fetch categories (also shows the API-down message) and any statement already in memory.
  useEffect(() => {
    (async () => {
      try {
        setCategories(await getCategories());
        const existing = await getTransactions();
        if (existing.length > 0) {
          setRows(existing);
          setSummary(await getSummary());
        }
      } catch (e) {
        setUploadError(errorText(e));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setFileName(file.name);
    try {
      const res = await uploadCsv(file);
      setRows(res.transactions);
      setSkipped(res.skipped_rows);
      setTab("all");
      setCategory("");
      setQuery("");
      setRowErrors({});
      await refreshSummary();
    } catch (e) {
      setUploadError(errorText(e));
    } finally {
      setUploading(false);
    }
  }

  function showToast(message: string) {
    clearTimeout(toastTimer.current);
    setToast(message);
    toastTimer.current = setTimeout(() => setToast(null), 3000);
  }

  async function onEdit(id: number, target: string) {
    setSavingId(id);
    setRowErrors((prev) => Object.fromEntries(Object.entries(prev).filter(([k]) => Number(k) !== id)));
    try {
      setRows(await updateCategory(id, target));
      showToast(`Moved to ${target}`);
      await refreshSummary();
    } catch (e) {
      setRowErrors((prev) => ({ ...prev, [id]: errorText(e) }));
    } finally {
      setSavingId(null);
    }
  }

  const visible = useMemo(
    () => (rows ? applyFilters(rows, tab, category, query) : []),
    [rows, tab, category, query],
  );
  const byId = useMemo(() => new Map((rows ?? []).map((t) => [t.id, t])), [rows]);
  const usedCategories = useMemo(
    () => [...new Set((rows ?? []).map((t) => t.category))].sort(),
    [rows],
  );

  function showReview() {
    setTab("review");
    setCategory("");
    setQuery("");
    document.getElementById("transactions")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <>
      <header className="masthead">
        <div className="wrap">
          <h1>Statement Categorizer</h1>
          <p>Sort a PKR bank statement for tax time. Uncertain rows wait for your call.</p>
        </div>
      </header>
      <main className="wrap">
        <UploadZone uploading={uploading} error={uploadError} fileName={fileName} skipped={skipped} onFile={(f) => void onFile(f)} />

        {loading ? (
          <div className="skeleton" role="status" aria-label="Loading">
            <div className="sk-cards"><i /><i /><i /><i /></div>
            <i className="sk-block" />
          </div>
        ) : rows === null ? (
          <section className="empty">
            <h2>No statement yet</h2>
            <p>Upload a CSV above. Try <code>sample_statement_pkr.csv</code> from the repo to see how it works.</p>
          </section>
        ) : (
          <>
            {summary && (
              <>
                <SummaryCards summary={summary} reviewActive={tab === "review"} onReview={showReview} />
                <CategoryBars categories={summary.categories} />
              </>
            )}
            <section className="panel table-panel" id="transactions" aria-labelledby="tx-title">
              <h2 id="tx-title">Transactions</h2>
              <FilterBar
                tab={tab}
                category={category}
                query={query}
                categories={usedCategories}
                shown={visible.length}
                total={rows.length}
                onTab={setTab}
                onCategory={setCategory}
                onQuery={setQuery}
              />
              {visible.length === 0 ? (
                <p className="empty-inline">No rows match these filters. Clear the search or pick All.</p>
              ) : (
                <TransactionsTable
                  rows={visible}
                  byId={byId}
                  categories={categories}
                  savingId={savingId}
                  rowErrors={rowErrors}
                  onEdit={(id, c) => void onEdit(id, c)}
                />
              )}
            </section>
          </>
        )}
      </main>
      <div className="toast" role="status" aria-live="polite" hidden={!toast}>{toast}</div>
    </>
  );
}
