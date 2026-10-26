import { useCallback, useEffect, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  ArrowRightLeft,
  BriefcaseBusiness,
  Check,
  Database,
  Download,
  FileSpreadsheet,
  LayoutDashboard,
  ListFilter,
  LoaderCircle,
  ReceiptText,
  ShieldCheck,
  ShoppingCart,
  Tag,
  Upload,
} from "lucide-react";
import { api, money, title } from "./api";
import type { Transaction, Workspace } from "./types";
import ImportDialog from "./ImportDialog";
import ReviewPanel from "./ReviewPanel";
import TransactionTable from "./TransactionTable";

const nav = [
  { name: "Overview", icon: LayoutDashboard },
  { name: "Transactions", icon: ReceiptText },
  { name: "Rules", icon: Tag },
  { name: "Statements", icon: FileSpreadsheet },
];

export default function App() {
  const [data, setData] = useState<Workspace | null>(null);
  const [section, setSection] = useState("Transactions");
  const [upload, setUpload] = useState(false);
  const [selected, setSelected] = useState<Transaction | null>(null);
  const [currency, setCurrency] = useState("PKR");
  const [account, setAccount] = useState("all");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState("");
  const refresh = useCallback(async () => {
    const next = await api<Workspace>("/workspace");
    setData(next);
  }, []);
  useEffect(() => {
    void refresh().catch((e) => setError(e.message));
  }, [refresh]);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 4000);
    return () => clearTimeout(timer);
  }, [toast]);
  async function demo() {
    setBusy(true);
    setError("");
    try {
      await api("/demo", { method: "POST" });
      await refresh();
      setToast("Demo statement imported. All details are fictional.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function removeRule(id: string) {
    try {
      await api(`/rules/${id}`, { method: "DELETE" });
      await refresh();
      setToast("Rule deleted. Existing reviews are unchanged.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function removeStatement(id: string) {
    if (
      !window.confirm(
        "Remove this statement and all its transactions and reviews? Saved rules will remain.",
      )
    )
      return;
    try {
      await api(`/statements/${id}`, { method: "DELETE" });
      await refresh();
      setSelected(null);
      setToast("Statement removed. You can import a corrected file.");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const rows = (data?.transactions || []).filter(
    (r) =>
      r.currency === currency && (account === "all" || r.account === account),
  );
  const totals = data?.summary.currencies[currency];
  const reviewCount = rows.filter((r) => r.needs_review).length;
  const currencies = Array.from(
    new Set(["PKR", ...Object.keys(data?.summary.currencies || {})]),
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setSection("Transactions");
          }}
        >
          <span className="brand-symbol">
            <Check size={22} />
          </span>
          SortedHisab<span className="brand-dot">.</span>
        </a>
        <div className="sidebar-caption">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {nav.map(({ name, icon: Icon }) => (
            <button
              key={name}
              className={section === name ? "selected" : ""}
              onClick={() => {
                setSection(name);
                setSelected(null);
              }}
            >
              <Icon size={19} />
              {name}
              {name === "Transactions" && data?.summary.needs_review ? (
                <span>{data.summary.needs_review}</span>
              ) : null}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div>
            <Database size={17} /> Local workspace
          </div>
          <small>
            <span className="online-dot" /> Your records stay on this device
          </small>
          <p>
            Built for independent developers.
            <br />A little less admin. A little more clarity.
          </p>
        </div>
      </aside>
      <main>
        <header className="page-header">
          <div>
            <h1>{section}</h1>
            <p>
              {section === "Transactions"
                ? "Every rupee, in the right place."
                : section === "Overview"
                  ? "A clearer picture of work and life."
                  : section === "Rules"
                    ? "Your decisions, remembered."
                    : "Your statements, accounted for."}
            </p>
          </div>
          <div className="header-actions">
            <a className="button secondary" href="/api/export/transactions">
              <Download size={16} /> Export CSV
            </a>
            <button className="primary" onClick={() => setUpload(true)}>
              <Upload size={17} /> Upload statement
            </button>
          </div>
        </header>
        {error ? (
          <div role="alert" className="error">
            {error}
            <button
              className="text-button"
              onClick={() => {
                setError("");
                void refresh().catch((e) => setError(e.message));
              }}
            >
              Retry
            </button>
          </div>
        ) : null}
        {!data && !error ? (
          <div className="loading">
            <LoaderCircle className="spin" /> Opening your workspace…
          </div>
        ) : null}
        {data && !data.transactions.length ? (
          <section className="welcome">
            <span className="welcome-icon">
              <ReceiptText size={36} />
            </span>
            <h2>
              Mixed statements.
              <br />
              <span>Sorted, with a little help from you.</span>
            </h2>
            <p>
              AI subscriptions, grocery runs, family transfers. Separate work
              from everyday life with clear rules and a review for every
              uncertain decision.
            </p>
            <div>
              <button className="primary" onClick={() => setUpload(true)}>
                <Upload size={17} /> Upload your first statement
              </button>
              <button
                className="secondary"
                disabled={busy}
                onClick={() => void demo()}
              >
                {busy ? "Loading…" : "Explore a demo"}
                <ArrowRight size={16} />
              </button>
            </div>
            <footer>
              <ShieldCheck size={16} /> No AI classification. No account
              connection. Fully explainable.
            </footer>
            <small>
              Use synthetic data for this assessment. Demo transactions are
              fictional.
            </small>
          </section>
        ) : null}
        {data && data.transactions.length ? (
          <>
            <div className="workspace-filters">
              <span>
                <span className="online-dot" /> {data.statements.length}{" "}
                statement{data.statements.length !== 1 ? "s" : ""} imported
              </span>
              <div>
                <select
                  aria-label="Select account"
                  value={account}
                  onChange={(e) => {
                    setAccount(e.target.value);
                    setSelected(null);
                  }}
                >
                  <option value="all">All accounts</option>
                  {Array.from(
                    new Set(data.transactions.map((r) => r.account)),
                  ).map((a) => (
                    <option key={a}>{a}</option>
                  ))}
                </select>
                <select
                  aria-label="Select currency"
                  value={currency}
                  onChange={(e) => {
                    setCurrency(e.target.value);
                    setSelected(null);
                  }}
                >
                  {currencies.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="metrics">
              <div className="metric business-metric">
                <span className="metric-icon">
                  <BriefcaseBusiness size={21} />
                </span>
                <div>
                  <span>Business expenses</span>
                  <strong>{money(totals?.business || 0, currency)}</strong>
                  <small>Allocated & reviewed · all accounts</small>
                </div>
              </div>
              <div className="metric personal-metric">
                <span className="metric-icon">
                  <ShoppingCart size={21} />
                </span>
                <div>
                  <span>Personal spending</span>
                  <strong>{money(totals?.personal || 0, currency)}</strong>
                  <small>Including personal share · all accounts</small>
                </div>
              </div>
              <div className="metric">
                <span className="metric-icon">
                  <ArrowRightLeft size={21} />
                </span>
                <div>
                  <span>Excluded movements</span>
                  <strong>{money(totals?.excluded || 0, currency)}</strong>
                  <small>Transfers, cash & repayments · all accounts</small>
                </div>
              </div>
              <div className="metric review-metric">
                <span className="metric-icon">
                  <AlertTriangle size={21} />
                </span>
                <div>
                  <span>Needs review</span>
                  <strong>
                    {reviewCount} <span>transactions</span>
                  </strong>
                  <small>In the selected account & currency</small>
                </div>
              </div>
            </div>
            {section === "Transactions" ? (
              <>
                <div className={`work-area ${selected ? "with-review" : ""}`}>
                  <div className="table-area">
                    {reviewCount ? (
                      <div className="review-banner">
                        <AlertTriangle size={19} />
                        <span>
                          <strong>
                            {reviewCount} transactions need your review.
                          </strong>{" "}
                          A good question beats a wrong guess.
                        </span>
                        <button
                          className="text-button"
                          onClick={() =>
                            setSelected(
                              rows.find((r) => r.needs_review) || null,
                            )
                          }
                        >
                          Start review
                          <ArrowRight size={15} />
                        </button>
                      </div>
                    ) : (
                      <div className="done-banner">
                        <Check size={18} /> All transactions in this view are
                        categorized. You can review any row.
                      </div>
                    )}
                    <TransactionTable
                      rows={rows}
                      selected={selected?.id}
                      onSelect={setSelected}
                    />
                    <div className="accounting-note">
                      <ShieldCheck size={15} />
                      <span>
                        Rule-based decisions. Original descriptions preserved.
                        Uncertainty stays visible.
                      </span>
                    </div>
                  </div>
                  {selected ? (
                    <ReviewPanel
                      key={selected.id}
                      row={selected}
                      data={data}
                      onClose={() => setSelected(null)}
                      onSaved={async () => {
                        await refresh();
                        setToast("Review saved. Totals updated.");
                      }}
                    />
                  ) : null}
                </div>
              </>
            ) : null}
            {section === "Overview" ? (
              <section className="overview-grid">
                <div className="surface">
                  <header>
                    <h2>Where the money went</h2>
                    <a className="text-button" href="/api/export/summary">
                      Export totals
                      <Download size={14} />
                    </a>
                  </header>
                  <p className="hint">
                    {currency} · all accounts · net expenses after refunds
                  </p>
                  {Object.entries(totals?.categories || {})
                    .sort((a, b) => b[1] - a[1])
                    .map(([category, amount]) => (
                      <div className="category-total" key={category}>
                        <div>
                          <span>{category}</span>
                          <strong>{money(amount, currency)}</strong>
                        </div>
                        <div className="bar-track">
                          <span
                            style={{
                              width: `${Math.min(100, Math.max(2, (Math.abs(amount) / (totals?.gross_expenses || 1)) * 100))}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                </div>
                <div className="surface reconciliation">
                  <h2>Every row accounted for</h2>
                  <p className="hint">
                    {currency} · all accounts · amounts never combined across
                    currencies
                  </p>
                  {[
                    ["Money out", totals?.money_out],
                    ["Money in", totals?.money_in],
                    ["Net movement", totals?.net_movement],
                    ["Gross expenses", totals?.gross_expenses],
                    ["Refunds", totals?.refunds],
                    ["Net expenses", totals?.net_expenses],
                    ["Confirmed business share", totals?.business],
                    ["Personal share", totals?.personal],
                    ["Expense purpose unresolved", totals?.unallocated],
                    ["Income candidates", totals?.income],
                    [
                      "Unresolved other movement (signed)",
                      totals?.unresolved_credits,
                    ],
                  ].map(([label, amount]) => (
                    <div key={String(label)}>
                      <span>{label}</span>
                      <strong>{money(Number(amount || 0), currency)}</strong>
                    </div>
                  ))}
                  <p className="warning reason">
                    {data.summary.needs_review} rows still need review across
                    the workspace. Categories do not establish tax treatment.
                  </p>
                </div>
              </section>
            ) : null}
            {section === "Statements" ? (
              <section className="surface">
                <header>
                  <h2>Import history</h2>
                  <span className="muted">
                    {data.statements.length} statements
                  </span>
                </header>
                <div className="statement-list">
                  {data.statements.map((s) => (
                    <article key={s.id}>
                      <span className="file-icon">
                        <FileSpreadsheet size={23} />
                      </span>
                      <div>
                        <h3>{s.filename}</h3>
                        <p>
                          {s.account} · {title(s.account_type)}
                        </p>
                        <small>
                          {s.period_start} — {s.period_end}
                        </small>
                      </div>
                      <span className="statement-count">
                        {s.row_count} rows<small>Imported</small>
                      </span>
                      <button
                        className="text-button"
                        onClick={() => void removeStatement(s.id)}
                      >
                        Remove
                      </button>
                    </article>
                  ))}
                </div>
                <p className="hint">
                  Exact files are blocked per account. Overlapping rows are
                  flagged for review and retained.
                </p>
              </section>
            ) : null}
            {section === "Rules" ? (
              <section className="surface">
                <header>
                  <h2>Your saved rules</h2>
                  <span className="muted">
                    {data.rules.length} exact matches
                  </span>
                </header>
                <p className="hint">
                  Rules match the full normalized description within one
                  account, on future imports. Structural payment and refund
                  rules take priority.
                </p>
                {data.rules.length ? (
                  data.rules.map((r) => (
                    <article className="rule-row" key={r.id}>
                      <Tag size={20} />
                      <div>
                        <strong>{r.match_text}</strong>
                        <p>
                          {r.account} · {r.category} · {title(r.purpose)}
                          {r.business_percent
                            ? ` · ${r.business_percent}% business`
                            : ""}
                        </p>
                      </div>
                      <button
                        className="secondary"
                        onClick={() => void removeRule(r.id)}
                      >
                        Delete rule
                      </button>
                    </article>
                  ))
                ) : (
                  <div className="empty-table">
                    <ListFilter size={30} />
                    <h3>Your judgment becomes a rule</h3>
                    <p>
                      Review a purchase or transfer and choose “Remember this
                      exact description”.
                    </p>
                  </div>
                )}
              </section>
            ) : null}
          </>
        ) : null}
        <footer className="page-footer">
          <span>
            SortedHisab <span className="muted">/</span> Made for the
            independent life.
          </span>
          <span>Local-first · Deterministic · Explainable</span>
        </footer>
      </main>
      {upload ? (
        <ImportDialog
          onClose={() => setUpload(false)}
          onImported={async () => {
            await refresh();
            setSection("Transactions");
            setToast("Statement imported. Ready for review.");
          }}
        />
      ) : null}
      {toast ? (
        <div className="toast" role="status">
          <Check size={17} />
          {toast}
        </div>
      ) : null}
    </div>
  );
}
