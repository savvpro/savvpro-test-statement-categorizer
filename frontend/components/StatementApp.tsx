"use client";

import { useEffect, useRef, useState } from "react";
import { FileNotices } from "@/components/FileNotices";
import { ReviewBar } from "@/components/ReviewBar";
import { StatementSummary } from "@/components/StatementSummary";
import { TransactionTable } from "@/components/TransactionTable";
import { UploadPanel } from "@/components/UploadPanel";
import { exportUrl, fetchSampleFile, fixTransaction, uploadStatement } from "@/lib/api";
import { plural } from "@/lib/format";
import { NEEDS_REVIEW, type Statement, type Txn } from "@/lib/types";
import { btnPrimary, btnSecondary } from "@/lib/ui";

interface Notice {
  kind: "ok" | "error";
  text: string;
}

const messageOf = (e: unknown) =>
  e instanceof Error ? e.message : "Something went wrong. Please try again.";

export function StatementApp() {
  const [statement, setStatement] = useState<Statement | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [pending, setPending] = useState<ReadonlySet<string>>(new Set());
  const [updated, setUpdated] = useState<ReadonlySet<string>>(new Set());
  const [onlyReview, setOnlyReview] = useState(false);

  const headingRef = useRef<HTMLHeadingElement>(null);
  const tableRef = useRef<HTMLElement>(null);
  const clearTimer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  // When results appear, move focus to them so keyboard and screen-reader users land there.
  const statementId = statement?.id;
  useEffect(() => {
    if (statementId) headingRef.current?.focus();
  }, [statementId]);
  useEffect(() => () => clearTimeout(clearTimer.current), []);

  async function load(getFile: () => Promise<File>, purchasesPositive: boolean) {
    setBusy(true);
    setError(null);
    try {
      const next = await uploadStatement(await getFile(), purchasesPositive);
      setStatement(next);
      setOnlyReview(false);
      setNotice(null);
      setUpdated(new Set());
    } catch (e) {
      setError(messageOf(e));
    } finally {
      setBusy(false);
    }
  }

  async function fix(txn: Txn, category: string) {
    if (!statement || category === txn.category) return;
    setPending((p) => new Set(p).add(txn.id));
    setNotice(null);
    try {
      const result = await fixTransaction(statement.id, txn.id, category);
      setStatement(result.statement);

      setUpdated(new Set(result.updated_ids));
      clearTimeout(clearTimer.current);
      clearTimer.current = setTimeout(() => setUpdated(new Set()), 3000);

      const extra = result.updated_ids.length;
      setNotice({
        kind: "ok",
        text:
          `Saved “${txn.description}” as ${category}.` +
          (extra ? ` Also applied to ${plural(extra, "similar row")}.` : ""),
      });
    } catch (e) {
      setNotice({ kind: "error", text: messageOf(e) });
    } finally {
      setPending((p) => {
        const next = new Set(p);
        next.delete(txn.id);
        return next;
      });
    }
  }

  function showReviewRows() {
    setOnlyReview(true);
    tableRef.current?.scrollIntoView({ block: "start" });
  }

  const visible = statement
    ? onlyReview
      ? statement.transactions.filter((t) => t.category === NEEDS_REVIEW)
      : statement.transactions
    : [];

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col px-4 sm:px-6">
      <header className="flex items-center justify-between gap-4 border-b border-rule py-4">
        <span className="text-sm font-semibold tracking-tight">Statement Categorizer</span>
        {statement && (
          <button
            type="button"
            className={btnSecondary}
            onClick={() => {
              setStatement(null);
              setNotice(null);
            }}
          >
            Upload another
          </button>
        )}
      </header>

      <main className="flex-1 py-10">
        {error && (
          <p
            role="alert"
            className="mb-8 rounded-md border border-neg bg-danger-bg px-4 py-3 text-sm text-neg"
          >
            {error}
          </p>
        )}

        {!statement ? (
          <UploadPanel
            busy={busy}
            onUpload={(file, positive) => load(async () => file, positive)}
            onSample={(positive) => load(fetchSampleFile, positive)}
          />
        ) : (
          <div className="space-y-10">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div className="min-w-0">
                <h1
                  ref={headingRef}
                  tabIndex={-1}
                  className="text-2xl font-semibold tracking-tight break-words focus:outline-none"
                >
                  {statement.filename}
                </h1>
                <p className="mt-1 text-sm text-ink-2">
                  {plural(statement.summary.total_transactions, "transaction")} read
                </p>
              </div>
              <a href={exportUrl(statement.id)} download className={btnPrimary}>
                Export CSV
              </a>
            </div>

            <FileNotices skipped={statement.skipped} warnings={statement.warnings} />

            <StatementSummary statement={statement} onReview={showReviewRows} />

            <section ref={tableRef} aria-labelledby="transactions-heading" className="scroll-mt-4">
              <ReviewBar
                total={statement.summary.total_transactions}
                needsReview={statement.summary.needs_review}
                onlyReview={onlyReview}
                onFilter={setOnlyReview}
              />

              <div role="status" aria-live="polite" className="mt-3 min-h-6 text-sm">
                {notice && (
                  <span className={notice.kind === "error" ? "text-neg" : "text-ink-2"}>
                    {notice.text}
                  </span>
                )}
              </div>

              <div className="mt-2">
                {visible.length === 0 ? (
                  <p className="border-y border-rule py-10 text-center text-sm text-ink-2">
                    Nothing left to review.{" "}
                    <button
                      type="button"
                      className="font-medium text-accent underline underline-offset-2"
                      onClick={() => setOnlyReview(false)}
                    >
                      Show all rows
                    </button>
                  </p>
                ) : (
                  <TransactionTable
                    transactions={visible}
                    categories={statement.categories}
                    pending={pending}
                    updated={updated}
                    onFix={fix}
                  />
                )}
              </div>
            </section>
          </div>
        )}
      </main>

      <footer className="border-t border-rule py-6 text-xs leading-relaxed text-ink-3">
        Categories are decided by plain rules in this project, not by an AI model. Uploaded
        statements are held in server memory only and are never written to disk. Totals are
        estimates, not tax advice.
      </footer>
    </div>
  );
}
