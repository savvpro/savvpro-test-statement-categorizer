"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { BookOpenCheck, FileSpreadsheet, Loader2, ReceiptText, Upload } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  ApiError,
  DEFAULT_CATEGORIES,
  api,
  errorMessage,
  type Statement,
  type Summary,
  type Transaction,
} from "@/lib/api";
import { LearnedRules, StatementsList } from "./ListViews";
import { Shell, type View } from "./Shell";
import { StatCardsSkeleton, StatementView, TableSkeleton, type Tab } from "./StatementView";
import { UploadDropzone, validateCsv } from "./UploadDropzone";
import { IconCircle, Notice, buttonPrimary, buttonSecondary } from "./ui";

const STORAGE_KEY = "ledgerlite:statementId";
const VIEWS: View[] = ["dashboard", "statements", "review", "rules"];

function readStoredId(): number | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    const n = raw ? Number(raw) : NaN;
    return Number.isInteger(n) && n > 0 ? n : null;
  } catch {
    return null;
  }
}

function storeId(id: number | null) {
  try {
    if (id === null) window.localStorage.removeItem(STORAGE_KEY);
    else window.localStorage.setItem(STORAGE_KEY, String(id));
  } catch {
    /* storage unavailable (private mode); URL still carries the id */
  }
}

function parseId(raw: string | null): number | null {
  const n = raw ? Number(raw) : NaN;
  return Number.isInteger(n) && n > 0 ? n : null;
}

const HEADERS: Record<View, { icon: LucideIcon; title: string; subtitle: string }> = {
  dashboard: {
    icon: ReceiptText,
    title: "Statement review",
    subtitle: "Every transaction gets a category and a reason. Anything uncertain waits in Needs Review.",
  },
  review: {
    icon: ReceiptText,
    title: "Statement review",
    subtitle: "Rows LedgerLite was not sure about. Pick a category and it will remember the merchant.",
  },
  statements: {
    icon: FileSpreadsheet,
    title: "Statements",
    subtitle: "Every CSV you have uploaded. Open one to keep reviewing it.",
  },
  rules: {
    icon: BookOpenCheck,
    title: "Learned rules",
    subtitle: "Merchants LedgerLite learned from your corrections.",
  },
};

export function Dashboard() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const viewParam = params.get("view");
  const view: View = VIEWS.includes(viewParam as View) ? (viewParam as View) : "dashboard";
  const urlId = parseId(params.get("id"));

  const [statementId, setStatementId] = useState<number | null>(urlId);
  const [statement, setStatement] = useState<Statement | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  const [categories, setCategories] = useState<string[]>(DEFAULT_CATEGORIES);
  const [tab, setTab] = useState<Tab>(view === "review" ? "needs_review" : "all");

  const [busy, setBusy] = useState<"upload" | "sample" | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const [savingId, setSavingId] = useState<number | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const fileInput = useRef<HTMLInputElement>(null);
  const requestSeq = useRef(0);
  const missingId = useRef<number | null>(null);

  const setUrl = useCallback(
    (next: { view?: View; id?: number | null }) => {
      const q = new URLSearchParams(params.toString());
      const v = next.view ?? view;
      if (v === "dashboard") q.delete("view");
      else q.set("view", v);
      if (next.id !== undefined) {
        if (next.id === null) q.delete("id");
        else q.set("id", String(next.id));
      }
      const qs = q.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, pathname, router, view],
  );

  // Fetch statement + summary. `quiet` keeps the current data on screen (used after edits).
  const load = useCallback(async (id: number, opts: { quiet?: boolean; fromStorage?: boolean } = {}) => {
    const seq = ++requestSeq.current;
    if (!opts.quiet) {
      setLoading(true);
      setLoadError(null);
    }
    const [st, sm] = await Promise.allSettled([api.getStatement(id), api.getSummary(id)]);
    if (seq !== requestSeq.current) return;

    if (st.status === "fulfilled") {
      setStatement(st.value);
      setLoadError(null);
      storeId(id);
    } else {
      const err = st.reason;
      if (err instanceof ApiError && err.status === 404) {
        missingId.current = id;
        storeId(null);
        setStatement(null);
        setStatementId(null);
        setLoadError(opts.fromStorage ? null : `Statement #${id} was not found. It may have been removed.`);
      } else if (!opts.quiet) {
        setStatement(null);
        setLoadError(errorMessage(err));
      } else {
        setSaveError(`Saved, but could not refresh the statement: ${errorMessage(err)}`);
      }
    }
    if (sm.status === "fulfilled") {
      setSummary(sm.value);
      setSummaryError(null);
    } else if (st.status === "fulfilled") {
      setSummaryError(errorMessage(sm.reason));
    }
    setLoading(false);
  }, []);

  // Initial: URL id wins, then the last statement from localStorage.
  useEffect(() => {
    const id = urlId ?? readStoredId();
    setReady(true);
    if (id) {
      setStatementId(id);
      if (!urlId) setUrl({ id });
      void load(id, { fromStorage: !urlId });
    }
    // run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Follow back/forward or manual edits of ?id=
  useEffect(() => {
    if (ready && urlId && urlId !== statementId && urlId !== missingId.current) {
      setStatementId(urlId);
      void load(urlId);
    }
  }, [urlId, ready, statementId, load]);

  useEffect(() => {
    api
      .categories()
      .then((list) => {
        if (Array.isArray(list) && list.length) setCategories(list);
      })
      .catch(() => {
        /* keep the contract's fixed list */
      });
  }, []);

  const navigate = (v: View) => {
    if (v === "review") setTab("needs_review");
    else if (v === "dashboard") setTab("all");
    setUrl({ view: v });
  };

  const openStatement = (id: number) => {
    setSummary(null);
    setSaveMessage(null);
    setSaveError(null);
    setTab("all");
    setStatementId(id);
    setUrl({ view: "dashboard", id });
    void load(id);
  };

  const afterCreate = async (st: Statement) => {
    setStatement(st);
    setSummary(null);
    setSummaryError(null);
    setSaveMessage(null);
    setSaveError(null);
    setLoadError(null);
    setTab("all");
    setStatementId(st.id);
    storeId(st.id);
    setUrl({ view: view === "review" ? "review" : "dashboard", id: st.id });
    await load(st.id, { quiet: true });
  };

  const handleFile = async (file: File) => {
    const problem = validateCsv(file);
    if (problem) {
      setUploadError(problem);
      return;
    }
    setUploadError(null);
    setBusy("upload");
    try {
      await afterCreate(await api.uploadStatement(file));
    } catch (err) {
      setUploadError(`Upload failed: ${errorMessage(err)}`);
    } finally {
      setBusy(null);
    }
  };

  const handleSample = async () => {
    setUploadError(null);
    setBusy("sample");
    try {
      await afterCreate(await api.loadSample("messy"));
    } catch (err) {
      setUploadError(`Could not load the sample: ${errorMessage(err)}`);
    } finally {
      setBusy(null);
    }
  };

  const handleCategoryChange = async (tx: Transaction, category: string) => {
    if (category === tx.category) return;
    setSavingId(tx.id);
    setSaveError(null);
    setSaveMessage(null);
    try {
      const res = await api.updateCategory(tx.id, category);
      const merchant = tx.normalized_merchant || tx.description;
      const others = res.also_updated?.length ?? 0;
      let msg = `${merchant} set to ${category}.`;
      if (res.learned_rule) msg += ` LedgerLite will use this for ${res.learned_rule.merchant} from now on.`;
      if (others) msg += ` Also updated ${others} other ${others === 1 ? "row" : "rows"} from the same merchant.`;
      setSaveMessage(msg);
      if (statementId) await load(statementId, { quiet: true });
    } catch (err) {
      setSaveError(
        `Could not change the category for ${tx.normalized_merchant || tx.description}: ${errorMessage(err)}`,
      );
    } finally {
      setSavingId(null);
    }
  };

  const reviewCount = statement ? statement.transactions.filter((t) => t.needs_review).length : null;
  const header = HEADERS[view];
  const showUpload = view !== "rules";

  let body: React.ReactNode;
  if (view === "statements") {
    body = <StatementsList activeId={statementId} onOpen={openStatement} />;
  } else if (view === "rules") {
    body = <LearnedRules />;
  } else if (!ready || (loading && !statement)) {
    body = (
      <div className="space-y-6">
        <StatCardsSkeleton />
        <TableSkeleton />
      </div>
    );
  } else if (statement) {
    body = (
      <StatementView
        key={statement.id}
        statement={statement}
        summary={summary}
        summaryError={summaryError}
        categories={categories}
        tab={tab}
        onTabChange={setTab}
        savingId={savingId}
        saveMessage={saveMessage}
        saveError={saveError}
        onCategoryChange={handleCategoryChange}
        exportUrl={api.exportUrl(statement.id)}
      />
    );
  } else {
    body = (
      <div className="space-y-4">
        {loadError ? (
          <Notice
            tone="red"
            title="Could not open the statement"
            action={
              statementId ? (
                <button
                  type="button"
                  className={`${buttonSecondary} h-8 px-3 text-xs`}
                  onClick={() => load(statementId)}
                >
                  Retry
                </button>
              ) : undefined
            }
          >
            {loadError}
          </Notice>
        ) : null}
        <UploadDropzone busy={busy} error={uploadError} onFile={handleFile} onSample={handleSample} />
      </div>
    );
  }

  const dropzoneVisible = (view === "dashboard" || view === "review") && !statement;

  return (
    <Shell view={view} reviewCount={reviewCount} onNavigate={navigate}>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <IconCircle icon={header.icon} size="lg" square />
          <div className="min-w-0">
            <h1 className="text-xl font-semibold text-ink sm:text-2xl">{header.title}</h1>
            <p className="mt-0.5 text-sm text-muted">{header.subtitle}</p>
          </div>
        </div>
        {showUpload ? (
          <>
            <button
              type="button"
              className={`${buttonPrimary} w-full shrink-0 sm:w-auto`}
              onClick={() => fileInput.current?.click()}
              disabled={busy !== null}
            >
              {busy === "upload" ? (
                <Loader2 size={16} className="animate-spin" aria-hidden="true" />
              ) : (
                <Upload size={16} strokeWidth={1.75} aria-hidden="true" />
              )}
              {busy === "upload" ? "Uploading..." : "Upload statement"}
            </button>
            <input
              ref={fileInput}
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              tabIndex={-1}
              aria-hidden="true"
              onChange={(e) => {
                const file = e.target.files?.[0];
                e.target.value = "";
                if (file) void handleFile(file);
              }}
            />
          </>
        ) : null}
      </div>

      {uploadError && !dropzoneVisible ? (
        <div className="mb-6">
          <Notice tone="red" title="Upload failed">
            {uploadError.replace(/^Upload failed: /, "")}
          </Notice>
        </div>
      ) : null}

      {body}
    </Shell>
  );
}
