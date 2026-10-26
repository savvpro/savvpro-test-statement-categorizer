import { useEffect, useState } from "react";
import {
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Download,
  FileSpreadsheet,
  FolderOpen,
  LayoutDashboard,
  LoaderCircle,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Trash2,
  X,
} from "lucide-react";
import { api, ApiError, download, money } from "./api";
import { ErrorNotice, StatusBadge } from "./components";
import ImportWizard from "./ImportWizard";
import ReviewPanel from "./ReviewPanel";
import DeleteDialog from "./DeleteDialog";
import type {
  CategoryData,
  ReviewPatch,
  Statement,
  StatementEntry,
  Summary,
  Transaction,
  Workspace,
} from "./types";

const PAGE_SIZE = 40;
export default function App() {
  const [entries, setEntries] = useState<StatementEntry[]>([]);
  const [categories, setCategories] = useState<CategoryData | null>(null);
  const [statement, setStatement] = useState<Statement | null>(null);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [notice, setNotice] = useState("");
  const [status, setStatus] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [exporting, setExporting] = useState(false);

  async function refreshList() {
    const list = await api<StatementEntry[]>("/statements");
    setEntries(list);
    return list;
  }
  async function loadStatement(id: string) {
    setLoading(true);
    setError(null);
    setSelectedId(null);
    setDeleteConfirm(false);
    try {
      const snapshot = await api<Workspace>(`/statements/${id}/workspace`);
      setStatement(snapshot.statement);
      setSummary(snapshot.summary);
      setTransactions(snapshot.transactions);
      setImporting(false);
      setStatus("all");
      setSearch("");
      setPage(0);
      localStorage.setItem("ledgerlens.statement", id);
    } catch (e) {
      setError(asError(e));
    } finally {
      setLoading(false);
    }
  }
  async function initialize() {
    setInitializing(true);
    setError(null);
    try {
      const [list, cats] = await Promise.all([
        refreshList(),
        api<CategoryData>("/categories"),
      ]);
      setCategories(cats);
      const previous = localStorage.getItem("ledgerlens.statement");
      const chosen = list.find((e) => e.statement.id === previous) || list[0];
      if (chosen) await loadStatement(chosen.statement.id);
    } catch (e) {
      setError(asError(e));
    } finally {
      setInitializing(false);
    }
  }
  useEffect(() => {
    void initialize();
  }, []); // A single bootstrap; API state remains authoritative.
  useEffect(() => {
    setPage(0);
  }, [status, search]);
  useEffect(() => {
    if (!notice) return;
    const timer = setTimeout(() => setNotice(""), 6000);
    return () => clearTimeout(timer);
  }, [notice]);
  const selected = transactions.find((t) => t.id === selectedId);
  const filtered = transactions.filter(
    (row) =>
      (!search ||
        row.description.toLowerCase().includes(search.toLowerCase())) &&
      (status === "all" ||
        (status === "review" && row.needs_review) ||
        (status === "ready" &&
          !row.needs_review &&
          row.duplicate_status !== "excluded") ||
        (status === "excluded" && row.duplicate_status === "excluded")),
  );
  const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  function selectRow(id: string) {
    setSelectedId(id);
  }
  async function saveReview(patch: ReviewPatch) {
    if (!selected || !statement) return;
    setSaving(true);
    setError(null);
    try {
      await api<Transaction>(`/transactions/${selected.id}/review`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      const snapshot = await api<Workspace>(
        `/statements/${statement.id}/workspace`,
      );
      // Rows and totals are one database snapshot, including edits from other tabs.
      setTransactions(snapshot.transactions);
      setSummary(snapshot.summary);
      await refreshList();
      setNotice(
        patch.action === "reset"
          ? "Original engine decision restored."
          : patch.action === "duplicate"
            ? "Duplicate decision saved. Totals updated."
            : "Classification saved. Totals updated.",
      );
    } catch (e) {
      setError(asError(e));
    } finally {
      setSaving(false);
    }
  }
  async function reloadReview() {
    if (!statement) return;
    setSaving(true);
    try {
      const snapshot = await api<Workspace>(
        `/statements/${statement.id}/workspace`,
      );
      setTransactions(snapshot.transactions);
      setSummary(snapshot.summary);
      setError(null);
    } catch (e) {
      setError(asError(e));
    } finally {
      setSaving(false);
    }
  }
  function nextReview() {
    const remaining = transactions.filter(
      (t) => t.needs_review && t.id !== selectedId,
    );
    const next =
      remaining.find((t) => t.source_row > (selected?.source_row || 0)) ||
      remaining[0];
    if (next) setSelectedId(next.id);
    else if (selected?.needs_review) {
      setNotice(
        "This is the last review item. Resolve it before exporting a reviewed statement.",
      );
    } else {
      setSelectedId(null);
      setNotice("All review items are resolved. Your handoff is ready.");
    }
  }
  async function imported(meta: Statement, existing: boolean) {
    await refreshList();
    await loadStatement(meta.id);
    setNotice(
      existing
        ? "This exact statement was already imported. Your saved decisions are preserved."
        : `${meta.row_count} transactions imported. Every source row accounted for.`,
    );
  }
  async function exportFile(kind: "transactions" | "summary") {
    if (!statement) return;
    setExporting(true);
    setError(null);
    try {
      await download(
        `/statements/${statement.id}/export?kind=${kind}${summary?.provisional ? "" : "&reviewed_only=true"}`,
        `ledgerlens-${kind}.csv`,
      );
      setNotice(
        `${kind === "summary" ? "Summary" : "Transactions"} exported${summary?.provisional ? " with provisional status" : ""}.`,
      );
    } catch (e) {
      setError(asError(e));
    } finally {
      setExporting(false);
    }
  }
  async function remove() {
    if (!statement) return;
    setSaving(true);
    setError(null);
    try {
      await api(`/statements/${statement.id}`, { method: "DELETE" });
      setStatement(null);
      setSummary(null);
      setTransactions([]);
      setSelectedId(null);
      setDeleteConfirm(false);
      localStorage.removeItem("ledgerlens.statement");
      const list = await refreshList();
      if (list[0]) await loadStatement(list[0].statement.id);
      setNotice("Statement and its review history deleted from local storage.");
    } catch (e) {
      setError(asError(e));
    } finally {
      setSaving(false);
    }
  }
  const currency = statement?.currency || "USD";
  const totals = summary?.totals;
  const count = summary?.counts;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a href="/" className="brand" aria-label="LedgerLens home">
          <span className="brand-mark">
            <i />
            <i />
            <i />
          </span>
          <span>
            Ledger<span>Lens</span>
          </span>
        </a>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <button
          className={`nav-item ${!importing ? "selected" : ""}`}
          onClick={() => setImporting(false)}
        >
          <LayoutDashboard size={18} /> Overview
        </button>
        <button
          className={`nav-item ${importing ? "selected" : ""}`}
          disabled={saving || loading}
          onClick={() => setImporting(true)}
        >
          <Plus size={18} /> Import statement
        </button>
        <div className="sidebar-section-title">
          STATEMENTS <span>{entries.length}</span>
        </div>
        <div className="statement-list">
          {entries.map((entry) => (
            <button
              className={`statement-link ${entry.statement.id === statement?.id && !importing ? "active" : ""}`}
              key={entry.statement.id}
              disabled={loading || saving}
              onClick={() => void loadStatement(entry.statement.id)}
            >
              <FileSpreadsheet size={17} />
              <span>
                <b>{entry.statement.filename}</b>
                <small>
                  {entry.statement.row_count} transactions ·{" "}
                  {entry.statement.currency}
                </small>
              </span>
              {entry.summary.provisional && <i className="notification-dot" />}
            </button>
          ))}
          {!entries.length && (
            <p className="sidebar-empty">
              Your imported statements
              <br />
              will appear here.
            </p>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="local-badge">
            <span /> LOCAL WORKSPACE
          </div>
          <p>
            Your data stays on this device.
            <br />
            Your decisions stay yours.
          </p>
          <div className="profile">
            <span>LL</span>
            <div>
              <b>Independent workspace</b>
              <small>Personal · No account needed</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <strong>
              {importing
                ? "Import statement"
                : statement
                  ? "Statement overview"
                  : "Welcome"}
            </strong>
          </div>
          <div className="topbar-note">
            <ShieldCheck size={15} /> Private by design
          </div>
        </header>
        <main className="main-content">
          {error && (
            <div className="global-error">
              <ErrorNotice error={error} />
              <button
                className="text-button"
                onClick={() => {
                  setError(null);
                  void initialize();
                }}
              >
                Reload workspace
              </button>
            </div>
          )}
          {initializing || loading ? (
            <div className="loading-state" role="status">
              <LoaderCircle className="spin" size={28} />
              <h2>Bringing your records into focus…</h2>
              <p>Loading your local workspace.</p>
            </div>
          ) : importing ? (
            <ImportWizard
              onImported={imported}
              onCancel={() => setImporting(false)}
            />
          ) : !statement || !summary || !categories ? (
            <section className="welcome">
              <div className="eyebrow">LESS GUESSWORK. MORE CLARITY.</div>
              <h1>
                Understand every transaction.
                <br />
                <em>Trust every total.</em>
              </h1>
              <p className="welcome-copy">
                A thoughtful workspace for independent professionals.
                <br />
                Turn a messy statement into a clear, reviewed handoff.
              </p>
              <button
                className="button primary"
                onClick={() => setImporting(true)}
              >
                <Plus size={18} /> Import your first statement{" "}
                <ArrowRight size={17} />
              </button>
              <span className="welcome-note">
                Or explore a synthetic example inside. No signup needed.
              </span>
              <div className="welcome-cards">
                <div>
                  <FingerprintIcon />
                  <h3>Decisions you can inspect</h3>
                  <p>
                    Specific rules. Clear evidence. A visible reason behind
                    every category.
                  </p>
                </div>
                <div>
                  <CircleHelp size={24} />
                  <h3>Uncertainty, made useful</h3>
                  <p>
                    If the evidence isn’t clear, you decide. A thoughtful pause
                    beats a wrong guess.
                  </p>
                </div>
                <div>
                  <CheckCheck size={24} />
                  <h3>Totals that stay together</h3>
                  <p>
                    Refunds, transfers, and corrections accounted for. Ready for
                    your next step.
                  </p>
                </div>
              </div>
              <div className="welcome-footer">
                <ShieldCheck size={15} /> Built for local use · No runtime AI ·
                CSV in, clarity out
              </div>
            </section>
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">YOUR MONEY, MADE CLEAR</div>
                  <h1>
                    Statement overview<span className="heading-dot">.</span>
                  </h1>
                  <p>
                    <FileSpreadsheet size={15} />
                    {statement.filename}
                    <span className="dot-separator">·</span>
                    {statement.row_count} transactions
                    <span className="dot-separator">·</span>
                    {currency}
                  </p>
                </div>
                <div className="heading-actions">
                  <button
                    className="button secondary"
                    disabled={saving}
                    onClick={() => setImporting(true)}
                  >
                    <Plus size={16} /> Import CSV
                  </button>
                  <button
                    className="button primary"
                    disabled={exporting || saving || !!error}
                    onClick={() => void exportFile("transactions")}
                  >
                    <Download size={16} />
                    {exporting ? "Preparing…" : "Export transactions"}
                  </button>
                </div>
              </div>
              <section
                className={`review-banner ${summary.provisional ? "" : "complete"}`}
              >
                <div className="banner-icon">
                  {summary.provisional ? (
                    <CircleHelp size={23} />
                  ) : (
                    <CheckCheck size={23} />
                  )}
                </div>
                <div>
                  <h2>
                    {summary.provisional
                      ? `${count?.needs_review} transactions could use your judgment`
                      : "Every transaction accounted for."}
                  </h2>
                  <p>
                    {summary.provisional
                      ? "Review the uncertain ones. We’ll keep your totals provisional until everything is resolved."
                      : "Your statement is ready for handoff. You can still inspect or change any decision."}
                  </p>
                </div>
                <div className="review-progress">
                  <span>
                    {(count?.automatic || 0) +
                      (count?.reviewed || 0) +
                      (count?.excluded || 0)}{" "}
                    of {count?.total} resolved
                  </span>
                  <progress
                    aria-label="Review completion"
                    value={(count?.total || 0) - (count?.needs_review || 0)}
                    max={count?.total || 1}
                  />
                </div>
                <button
                  className="button banner-button"
                  onClick={() => {
                    setStatus(summary.provisional ? "review" : "all");
                    nextReview();
                  }}
                >
                  {summary.provisional ? "Start reviewing" : "Review complete"}{" "}
                  {summary.provisional ? (
                    <ArrowRight size={16} />
                  ) : (
                    <Check size={16} />
                  )}
                </button>
              </section>
              <section className="summary-grid" aria-label="Financial summary">
                <div className="metric-card primary-metric">
                  <div>
                    <span>Net categorized expenses</span>
                    <span
                      className={`mini-status ${summary.provisional ? "amber" : ""}`}
                    >
                      {summary.provisional ? "Provisional" : "Reviewed"}
                    </span>
                  </div>
                  <strong data-testid="net-expenses">
                    {money(totals?.net_expense_minor || 0, currency)}
                  </strong>
                  <p>Confirmed expense debits less refunds</p>
                  <div className="metric-split">
                    <span>
                      Expenses{" "}
                      <b>{money(totals?.expense_minor || 0, currency)}</b>
                    </span>
                    <span>
                      Refunds{" "}
                      <b>−{money(totals?.refund_minor || 0, currency)}</b>
                    </span>
                  </div>
                </div>
                <div className="metric-card">
                  <div>
                    <span>Money in</span>
                    <ArrowDownLeft size={18} />
                  </div>
                  <strong>
                    {money(totals?.incoming_minor || 0, currency)}
                  </strong>
                  <p>All included incoming movement</p>
                  <small>
                    Income <b>{money(totals?.income_minor || 0, currency)}</b>
                  </small>
                </div>
                <div className="metric-card">
                  <div>
                    <span>Money out</span>
                    <ArrowUpRight size={18} />
                  </div>
                  <strong>
                    {money(totals?.outgoing_minor || 0, currency)}
                  </strong>
                  <p>All included outgoing movement</p>
                  <small>
                    Transfers out{" "}
                    <b>{money(totals?.transfer_out_minor || 0, currency)}</b>
                  </small>
                </div>
                <div className="metric-card review-metric">
                  <div>
                    <span>Awaiting review</span>
                    <CircleHelp size={18} />
                  </div>
                  <strong>
                    {count?.needs_review}
                    <small> transactions</small>
                  </strong>
                  <p>Separated from categorized totals</p>
                  <small>
                    Out {money(totals?.unresolved_out_minor || 0, currency)}{" "}
                    <span>·</span> In{" "}
                    {money(totals?.unresolved_in_minor || 0, currency)}
                  </small>
                </div>
              </section>
              <div
                className={`workspace-grid ${selected ? "has-selection" : ""}`}
              >
                <section className="panel transaction-panel">
                  <div className="panel-header">
                    <div>
                      <h2>
                        Transactions{" "}
                        <span className="count-pill">{count?.total}</span>
                      </h2>
                      <p>Every row has a story. Here’s what we know.</p>
                    </div>
                    <div className="engine-label">
                      <Sparkles size={13} /> Deterministic engine
                    </div>
                  </div>
                  <div className="table-controls">
                    <div className="tabs" aria-label="Filter transactions">
                      {[
                        ["all", "All transactions"],
                        ["review", "Needs review"],
                        ["ready", "Ready"],
                        ["excluded", "Excluded"],
                      ].map(([value, label]) => (
                        <button
                          key={value}
                          className={status === value ? "active" : ""}
                          onClick={() => setStatus(value)}
                        >
                          {label}
                          {value === "review" && (
                            <span>{count?.needs_review}</span>
                          )}
                        </button>
                      ))}
                    </div>
                    <label className="search">
                      <Search size={15} />
                      <input
                        aria-label="Search transactions"
                        placeholder="Search transactions…"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                      />
                      {search && (
                        <button
                          className="icon-button"
                          aria-label="Clear search"
                          onClick={() => setSearch("")}
                        >
                          <X size={13} />
                        </button>
                      )}
                    </label>
                  </div>
                  <div className="table-scroll">
                    <table className="transactions-table">
                      <thead>
                        <tr>
                          <th>Transaction</th>
                          <th>Category</th>
                          <th>Status</th>
                          <th className="amount-cell">Amount</th>
                          <th>
                            <span className="sr-only">Open</span>
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {pageRows.map((row) => (
                          <tr
                            key={row.id}
                            className={`${selectedId === row.id ? "selected" : ""} ${row.duplicate_status === "excluded" ? "excluded-row" : ""}`}
                            onClick={() => selectRow(row.id)}
                          >
                            <td>
                              <div className="transaction-name">
                                <span
                                  className={`transaction-avatar ${row.kind}`}
                                >
                                  {row.description.slice(0, 1).toUpperCase()}
                                </span>
                                <span>
                                  <button
                                    className="row-link"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      selectRow(row.id);
                                    }}
                                  >
                                    {row.description}
                                  </button>
                                  <small>
                                    {row.date}
                                    <span>·</span>Row {row.source_row}
                                    {row.duplicate_status === "pending" && (
                                      <b className="duplicate-label">
                                        Possible duplicate
                                      </b>
                                    )}
                                  </small>
                                </span>
                              </div>
                            </td>
                            <td>
                              <span className="category-chip">
                                {categories.categories[row.category]}
                              </span>
                              {row.kind === "refund" && (
                                <small className="kind-note">
                                  Expense refund
                                </small>
                              )}
                              {row.kind === "transfer" && (
                                <small className="kind-note">
                                  Not spending
                                </small>
                              )}
                            </td>
                            <td>
                              <StatusBadge row={row} />
                            </td>
                            <td
                              className={`amount-cell ${row.amount_minor > 0 ? "positive" : ""}`}
                            >
                              {money(row.amount_minor, currency)}
                            </td>
                            <td>
                              <ChevronRight size={15} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {!pageRows.length && (
                    <div className="table-empty">
                      <Search size={26} />
                      <h3>No transactions in this view</h3>
                      <p>Try another filter or a different search.</p>
                      <button
                        className="text-button"
                        onClick={() => {
                          setSearch("");
                          setStatus("all");
                        }}
                      >
                        Show all transactions
                      </button>
                    </div>
                  )}
                  <div className="table-footer">
                    <span>
                      {filtered.length
                        ? `${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, filtered.length)} of ${filtered.length}`
                        : "0"}{" "}
                      transactions
                    </span>
                    <div>
                      <button
                        className="icon-button"
                        aria-label="Previous page"
                        disabled={page === 0}
                        onClick={() => setPage((v) => v - 1)}
                      >
                        <ChevronLeft size={16} />
                      </button>
                      <button
                        className="icon-button"
                        aria-label="Next page"
                        disabled={(page + 1) * PAGE_SIZE >= filtered.length}
                        onClick={() => setPage((v) => v + 1)}
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>
                  </div>
                </section>
                {selected ? (
                  <ReviewPanel
                    key={`${selected.id}-${selected.version}`}
                    row={selected}
                    currency={currency}
                    categories={categories}
                    busy={saving}
                    error={error}
                    onReload={() => void reloadReview()}
                    onSave={saveReview}
                    onClose={() => setSelectedId(null)}
                    onNext={nextReview}
                    duplicatePeers={transactions.filter(
                      (r) =>
                        r.duplicate_group === selected.duplicate_group &&
                        r.id !== selected.id,
                    )}
                  />
                ) : (
                  <aside className="insights-column">
                    <section className="panel category-panel">
                      <div className="panel-header">
                        <div>
                          <h2>Where it went</h2>
                          <p>Net categorized business expenses</p>
                        </div>
                      </div>
                      <div className="category-list">
                        {summary.categories.length ? (
                          summary.categories.map((c, i) => (
                            <div className="category-item" key={c.category}>
                              <div>
                                <span>
                                  <i
                                    style={{
                                      background: [
                                        "#195e51",
                                        "#5b8870",
                                        "#9fb69c",
                                        "#bca675",
                                        "#7f98a7",
                                      ][i % 5],
                                    }}
                                  />
                                  {c.label}
                                </span>
                                <b>{money(c.net_minor, currency)}</b>
                              </div>
                              <div className="category-bar">
                                <span
                                  style={{
                                    width: `${Math.max(2, Math.min(100, (Math.abs(c.net_minor) / Math.max(1, ...summary.categories.map((v) => Math.abs(v.net_minor)))) * 100))}%`,
                                  }}
                                />
                              </div>
                            </div>
                          ))
                        ) : (
                          <p className="muted">
                            Review transactions to build your category summary.
                          </p>
                        )}
                      </div>
                      <button
                        className="text-button category-export"
                        disabled={exporting || !!error}
                        onClick={() => void exportFile("summary")}
                      >
                        <Download size={14} /> Export category summary
                      </button>
                    </section>
                    <section className="clarity-note">
                      <div className="note-icon">
                        <ShieldCheck size={21} />
                      </div>
                      <h3>
                        A wrong guess costs more
                        <br />
                        than a quick review.
                      </h3>
                      <p>
                        Unknown merchants, unclear credits, and conflicting
                        evidence always come back to you.
                      </p>
                      <div>
                        <Check size={13} /> No AI making financial decisions
                      </div>
                    </section>
                  </aside>
                )}
              </div>
              <section className="panel reconciliation-panel">
                <details>
                  <summary>
                    <span>
                      <ShieldCheck size={17} /> Reconciliation & cash movement
                    </span>
                    <span className="reconciled">
                      <Check size={14} /> Balanced <ChevronRight size={15} />
                    </span>
                  </summary>
                  <div className="reconciliation-grid">
                    {[
                      ["Imported net movement", "imported_signed_minor"],
                      ["Included net movement", "included_signed_minor"],
                      ["Excluded duplicate net", "excluded_signed_minor"],
                      ["Transfer incoming", "transfer_in_minor"],
                      ["Transfer outgoing", "transfer_out_minor"],
                      ["Personal incoming", "personal_in_minor"],
                      ["Personal outgoing", "personal_out_minor"],
                      ["Unresolved incoming", "unresolved_in_minor"],
                      ["Unresolved outgoing", "unresolved_out_minor"],
                    ].map(([label, key]) => (
                      <div key={key}>
                        <span>{label}</span>
                        <b>{money(totals?.[key] || 0, currency)}</b>
                      </div>
                    ))}
                  </div>
                  <p>
                    Imported = included + excluded. Included = incoming −
                    outgoing. Pending duplicate candidates stay included in cash
                    movement and unresolved in category totals.
                  </p>
                </details>
              </section>
              <footer className="workspace-footer">
                <span>
                  <ShieldCheck size={14} /> Original rows preserved · Decisions
                  saved locally · {count?.excluded} duplicate rows excluded
                </span>
                <button
                  className="text-button danger"
                  onClick={() => setDeleteConfirm(true)}
                  disabled={saving}
                >
                  <Trash2 size={14} /> Delete statement
                </button>
              </footer>
            </>
          )}
        </main>
      </div>
      {notice && (
        <div className="toast" role="status">
          <CheckCheck size={18} />
          {notice}
          <button
            className="icon-button"
            aria-label="Dismiss notification"
            onClick={() => setNotice("")}
          >
            <X size={15} />
          </button>
        </div>
      )}
      {deleteConfirm && (
        <DeleteDialog
          filename={statement?.filename || "this statement"}
          busy={saving}
          onCancel={() => setDeleteConfirm(false)}
          onConfirm={() => void remove()}
        />
      )}
    </div>
  );
}
function asError(error: unknown) {
  return error instanceof ApiError
    ? error
    : new ApiError(
        error instanceof Error
          ? error.message
          : "Something went wrong. Please retry.",
      );
}
function FingerprintIcon() {
  return <FolderOpen size={24} />;
}
