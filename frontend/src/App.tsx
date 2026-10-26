import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorMessage } from "./api";
import { Icon } from "./components/Icon";
import { UploadForm } from "./components/UploadForm";
import { SummaryPanel } from "./components/SummaryPanel";
import { TransactionTable, type Filter } from "./components/TransactionTable";
import { ReviewDialog } from "./components/ReviewDialog";
import type {
  AuditEvent,
  Statement,
  StatementListItem,
  Transaction,
} from "./types";

export default function App() {
  const [statements, setStatements] = useState<StatementListItem[]>([]);
  const [statement, setStatement] = useState<Statement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [reviewing, setReviewing] = useState<Transaction | null>(null);
  const [activity, setActivity] = useState<AuditEvent[] | null>(null);
  const [exporting, setExporting] = useState(false);
  const sequence = useRef(0);
  const tableAnchor = useRef<HTMLDivElement>(null);

  const load = useCallback(async (id?: string) => {
    const request = ++sequence.current;
    setLoading(true);
    setError("");
    try {
      const items = await api.list();
      const chosen = id ?? items[0]?.id;
      const details = chosen ? await api.statement(chosen) : null;
      // Discard late responses from older selections (including React StrictMode effects).
      if (request === sequence.current) {
        setStatements(items);
        setStatement(details);
        setActivity(null);
      }
    } catch (err) {
      if (request === sequence.current) setError(errorMessage(err));
      throw err;
    } finally {
      if (request === sequence.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load().catch(() => {});
    return () => {
      sequence.current += 1;
    };
  }, [load]);

  async function imported(id: string, reused: boolean) {
    await load(id);
    setUploading(false);
    setFilter("all");
    setNotice(
      reused
        ? "This exact statement was already imported. Your saved decisions are unchanged."
        : "Statement imported. Uncertain transactions are waiting for your review.",
    );
  }

  function focusTransactions(next: Filter) {
    setFilter(next);
    setActivity(null);
    setUploading(false);
    setTimeout(
      () =>
        tableAnchor.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        }),
      0,
    );
  }

  async function exportFile(summary = false) {
    if (!statement) return;
    setExporting(true);
    setError("");
    try {
      await api.download(
        statement.id,
        statement.summary.review_count === 0,
        summary,
      );
      setNotice(
        `${statement.summary.review_count ? "Draft" : "Final"} ${summary ? "summary" : "transactions"} exported.`,
      );
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  async function showActivity() {
    if (!statement) return;
    setError("");
    const id = statement.id;
    const request = sequence.current;
    try {
      const events = await api.audit(id);
      if (request === sequence.current) {
        setActivity(events);
        setUploading(false);
      }
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function deleteImport() {
    if (
      !statement ||
      !window.confirm(
        `Delete ${statement.filename}, its transactions, and its review history? This cannot be undone.`,
      )
    )
      return;
    setLoading(true);
    setError("");
    try {
      await api.delete(statement.id);
      setStatement(null);
      await load();
      setNotice("Import deleted.");
    } catch (err) {
      setError(errorMessage(err));
      setLoading(false);
    }
  }

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className="sidebar">
        <a className="brand" href="/">
          <span className="brand-mark">
            L<span>↗</span>
          </span>
          ledgerly<span className="brand-dot">.</span>
        </a>
        <div className="workspace-badge">
          <span className="avatar">DS</span>
          <div>
            <strong>Design studio</strong>
            <small>Freelancer workspace</small>
          </div>
        </div>
        <span className="nav-label">WORKSPACE</span>
        <nav aria-label="Main navigation">
          <button
            className={
              activity === null && filter === "all" && !uploading
                ? "nav-item active"
                : "nav-item"
            }
            disabled={loading}
            onClick={() => focusTransactions("all")}
          >
            <Icon name="grid" />
            Overview
          </button>
          <button
            className={
              filter === "needs_review" && activity === null
                ? "nav-item active"
                : "nav-item"
            }
            disabled={!statement || loading}
            onClick={() => focusTransactions("needs_review")}
          >
            <Icon name="check" />
            Review queue
            {statement && (
              <span className="nav-count">
                {statement.summary.review_count}
              </span>
            )}
          </button>
          <button
            className={activity !== null ? "nav-item active" : "nav-item"}
            onClick={showActivity}
            disabled={!statement || loading}
          >
            <Icon name="clock" />
            Review history
          </button>
        </nav>
        <div className="nav-section-title">
          <span className="nav-label">STATEMENTS</span>
          <button
            className="icon-button"
            aria-label="Import another statement"
            disabled={loading}
            onClick={() => {
              setUploading(true);
              setActivity(null);
            }}
          >
            <Icon name="plus" size={17} />
          </button>
        </div>
        <div className="statement-list">
          {statements.length === 0 ? (
            <p className="small muted">Your imports will appear here.</p>
          ) : (
            statements.map((item) => (
              <button
                key={item.id}
                className={`statement-link ${statement?.id === item.id ? "selected" : ""}`}
                disabled={loading}
                onClick={() => {
                  setFilter("all");
                  setUploading(false);
                  void load(item.id).catch(() => {});
                }}
              >
                <Icon name="file" size={18} />
                <span>
                  <strong>{item.filename}</strong>
                  <small>
                    {item.transaction_count} transactions · {item.currency}
                  </small>
                </span>
              </button>
            ))
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="trust-card">
            <Icon name="shield" />
            <strong>Every decision, explained.</strong>
            <p>Transparent rules. Your final say.</p>
            <span>NO AI CATEGORIZATION</span>
          </div>
          <div className="local-status">
            <span className="status-dot green" />
            Local, single-user workspace
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div>
            Workspace <span>/</span>{" "}
            <strong>
              {activity !== null ? "Review history" : "Statement overview"}
            </strong>
          </div>
          <span className="demo-label">BUILT FOR FREELANCERS</span>
        </header>
        <main id="main">
          <div className="page-header">
            <div>
              <span className="eyebrow">
                LESS PAPERWORK. MORE PEACE OF MIND.
              </span>
              <h1>Your books, a little clearer.</h1>
              <p className="muted">
                Make sense of your spending. Keep the final say.
              </p>
            </div>
            <button
              className="button primary"
              onClick={() => {
                setUploading(true);
                setActivity(null);
              }}
              disabled={loading}
            >
              <Icon name="plus" size={18} />
              Import statement
            </button>
          </div>
          {error && (
            <div className="error-box global-message" role="alert">
              <span>{error}</span>
              <button
                className="button secondary small-button"
                onClick={() => void load(statement?.id).catch(() => {})}
              >
                Retry
              </button>
            </div>
          )}
          {notice && (
            <div className="notice" role="status">
              <Icon name="check" size={17} />
              <span>{notice}</span>
              <button
                className="icon-button"
                aria-label="Dismiss notification"
                onClick={() => setNotice("")}
              >
                <Icon name="close" size={15} />
              </button>
            </div>
          )}
          {loading && (
            <div className="loading" role="status">
              <span className="spinner" />
              Loading your workspace…
            </div>
          )}
          {(uploading || (!statement && !loading)) && (
            <UploadForm
              onImported={imported}
              onCancel={statement ? () => setUploading(false) : undefined}
            />
          )}
          {statement && !uploading && (
            <>
              <div className="statement-header">
                <div>
                  <span className="file-token">
                    <Icon name="file" size={17} />
                  </span>
                  <strong>{statement.filename}</strong>
                  <span>
                    {statement.currency} · {statement.transactions.length}{" "}
                    transactions
                  </span>
                </div>
                <div className="export-actions">
                  <button
                    className="button secondary small-button"
                    disabled={exporting || loading}
                    onClick={() => exportFile(true)}
                  >
                    Summary CSV
                  </button>
                  <button
                    className="button secondary small-button"
                    disabled={exporting || loading}
                    onClick={() => exportFile()}
                  >
                    <Icon name="download" size={16} />
                    {exporting
                      ? "Exporting…"
                      : statement.summary.review_count
                        ? "Export draft"
                        : "Export final"}
                  </button>
                </div>
              </div>
              {activity === null ? (
                <>
                  <SummaryPanel
                    statement={statement}
                    onReview={() =>
                      focusTransactions(
                        statement.summary.review_count ? "needs_review" : "all",
                      )
                    }
                  />
                  {statement.summary.review_count > 0 && (
                    <div className="review-banner">
                      <span className="banner-icon">
                        <Icon name="info" />
                      </span>
                      <div>
                        <strong>A few things need your eye.</strong>
                        <p>
                          {statement.summary.review_count} transactions are on
                          hold. Check their purpose so your totals stay
                          accurate.
                        </p>
                      </div>
                      <button
                        className="button text-button"
                        onClick={() => focusTransactions("needs_review")}
                      >
                        Review now <Icon name="arrow" size={17} />
                      </button>
                    </div>
                  )}
                  <div ref={tableAnchor} className="table-anchor">
                    <TransactionTable
                      key={statement.id}
                      rows={statement.transactions}
                      filter={filter}
                      onFilter={setFilter}
                      onReview={setReviewing}
                    />
                  </div>
                </>
              ) : (
                <section className="panel activity-panel">
                  <h2>Review history</h2>
                  <p className="muted">
                    Every manual change, with the original rule decision
                    preserved.
                  </p>
                  {activity.length === 0 ? (
                    <div className="empty-results">
                      <Icon name="clock" size={26} />
                      <h3>No reviews yet</h3>
                      <p>Your saved decisions will appear here.</p>
                    </div>
                  ) : (
                    <ol className="audit-list">
                      {activity.map((event) => (
                        <li key={event.id}>
                          <span className="audit-dot">
                            <Icon name="check" size={16} />
                          </span>
                          <div>
                            <strong>{event.new_value.description}</strong>
                            <p>
                              {event.previous_value.category} →{" "}
                              {event.new_value.category} ·{" "}
                              {event.new_value.excluded
                                ? "Excluded"
                                : event.new_value.kind}
                            </p>
                            {event.note && (
                              <p className="audit-note">{event.note}</p>
                            )}
                            <small>
                              {new Date(event.created_at).toLocaleString()} ·
                              Version {event.new_value.version}
                            </small>
                          </div>
                        </li>
                      ))}
                    </ol>
                  )}
                </section>
              )}
              <div className="workspace-footer">
                <span>
                  <Icon name="shield" size={15} />
                  Rules engine v{statement.engine_version} · Categories are
                  bookkeeping suggestions, not tax advice.
                </span>
                <button
                  className="delete-link"
                  onClick={deleteImport}
                  disabled={loading}
                >
                  Delete import
                </button>
              </div>
            </>
          )}
          {!statement && !loading && (
            <div className="how-it-works">
              {[
                {
                  n: "01",
                  title: "Bring the transactions",
                  text: "A CSV export from your business bank or card.",
                },
                {
                  n: "02",
                  title: "Let the rules do their part",
                  text: "Recognizable merchants get a clear explanation.",
                },
                {
                  n: "03",
                  title: "Review. Export. Done.",
                  text: "Resolve the unknowns and share your category totals.",
                },
              ].map((step) => (
                <div key={step.n}>
                  <span>{step.n}</span>
                  <h3>{step.title}</h3>
                  <p>{step.text}</p>
                </div>
              ))}
            </div>
          )}
        </main>
        <footer className="site-footer">
          Made for the business behind your creative work.
          <span>Ledgerly / 2026</span>
        </footer>
      </div>
      {reviewing && (
        <ReviewDialog
          key={reviewing.id}
          transaction={reviewing}
          onClose={() => setReviewing(null)}
          onSaved={() => load(statement!.id)}
        />
      )}
    </div>
  );
}
