import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { CategoryTotals } from "./components/CategoryTotals";
import { Notices } from "./components/Notices";
import { RulesPanel } from "./components/RulesPanel";
import { StatementList } from "./components/StatementList";
import { SummaryCards } from "./components/SummaryCards";
import { TransactionTable } from "./components/TransactionTable";
import { UploadPanel } from "./components/UploadPanel";
import { formatDate } from "./lib/format";
import type {
  Category,
  Rule,
  Sample,
  SignConvention,
  Statement,
  StatementListItem,
  Transaction,
} from "./types";

export default function App() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [statements, setStatements] = useState<StatementListItem[]>([]);
  const [statement, setStatement] = useState<Statement | null>(null);
  const [rules, setRules] = useState<Rule[]>([]);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [remember, setRemember] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categoryMap = useMemo(() => new Map(categories.map((c) => [c.id, c])), [categories]);

  const run = useCallback(async <T,>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true);
    setError(null);
    try {
      return await action();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      return undefined;
    } finally {
      setBusy(false);
    }
  }, []);

  const refreshSidebar = useCallback(async () => {
    const [list, learned] = await Promise.all([api.statements(), api.rules()]);
    setStatements(list);
    setRules(learned);
  }, []);

  useEffect(() => {
    void run(async () => {
      const [cats, list, learned, demo] = await Promise.all([
        api.categories(),
        api.statements(),
        api.rules(),
        api.samples(),
      ]);
      setCategories(cats);
      setStatements(list);
      setRules(learned);
      setSamples(demo);
      if (list.length > 0) setStatement(await api.statement(list[0].id));
    });
  }, [run]);

  const showStatement = (s: Statement | undefined) => {
    if (!s) return;
    setStatement(s);
    void refreshSidebar();
  };

  const upload = (file: File, convention: SignConvention) =>
    run(() => api.upload(file, convention)).then(showStatement);

  const importSample = (name: string) => run(() => api.importSample(name)).then(showStatement);

  const select = (id: number) => run(() => api.statement(id)).then((s) => s && setStatement(s));

  const remove = (id: number) =>
    run(async () => {
      await api.deleteStatement(id);
      if (statement?.id === id) setStatement(null);
      await refreshSidebar();
    });

  const categorize = (tx: Transaction, category: string | null) => {
    if (!statement) return;
    void run(() =>
      api.updateTransaction(statement.id, tx.id, category, remember && category !== null),
    ).then(showStatement);
  };

  const forgetRule = (rule: Rule) =>
    run(async () => {
      await api.deleteRule(rule);
      await refreshSidebar();
    });

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand__logo" aria-hidden>
            DL
          </span>
          <div>
            <h1>DriveLedger</h1>
            <p>Tax-time sorting for rideshare &amp; delivery drivers</p>
          </div>
        </div>
      </header>

      {error && (
        <div className="error" role="alert">
          <span>{error}</span>
          <button className="icon-btn" aria-label="Dismiss" onClick={() => setError(null)}>
            ×
          </button>
        </div>
      )}

      <div className="layout">
        <aside className="sidebar">
          <UploadPanel samples={samples} busy={busy} onUpload={upload} onSample={importSample} />
          <StatementList
            statements={statements}
            activeId={statement?.id ?? null}
            onSelect={select}
            onDelete={remove}
          />
          <RulesPanel rules={rules} categories={categoryMap} onDelete={forgetRule} />
        </aside>

        <main className="main">
          {statement ? (
            <>
              <div className="statement-head">
                <div>
                  <h2>{statement.filename}</h2>
                  <p className="muted">
                    {statement.period_start && statement.period_end
                      ? `${formatDate(statement.period_start)} – ${formatDate(statement.period_end)}`
                      : ""}
                    {" · "}
                    {statement.transaction_count} transactions
                  </p>
                </div>
                <a className="btn btn--ghost" href={api.exportUrl(statement.id)} download>
                  Export CSV
                </a>
              </div>
              <Notices warnings={statement.warnings} skipped={statement.skipped} />
              <SummaryCards summary={statement.summary} />
              <div className="content-grid">
                <TransactionTable
                  key={statement.id}
                  transactions={statement.transactions}
                  categories={categories}
                  categoryMap={categoryMap}
                  busy={busy}
                  remember={remember}
                  onRememberChange={setRemember}
                  onChange={categorize}
                />
                <CategoryTotals summary={statement.summary} />
              </div>
            </>
          ) : (
            <div className="welcome">
              <h2>Sort a year of driving in minutes</h2>
              <ol>
                <li>Upload a CSV or OFX export from your bank or credit card.</li>
                <li>
                  Every transaction is sorted into a Schedule C category: gig income, fuel, tolls,
                  phone, insurance… Transfers and personal spending are kept out of the totals.
                </li>
                <li>
                  Anything the app isn&apos;t sure about lands in <strong>Needs review</strong>. Fix
                  it once and it remembers that merchant next time.
                </li>
              </ol>
              <p className="muted small">
                Decisions are made by transparent rules, never by an AI model. Click any status
                badge to see why.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
