import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  CheckCheck,
  ChevronRight,
  CircleHelp,
  Download,
  FileClock,
  FileSpreadsheet,
  FolderOpen,
  LayoutDashboard,
  Leaf,
  ListFilter,
  LoaderCircle,
  LockKeyhole,
  Plus,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { api, money, shortDate } from "./api";
import { CategoryBreakdown } from "./components/CategoryBreakdown";
import { ReviewDialog } from "./components/ReviewDialog";
import { SummaryCards } from "./components/SummaryCards";
import { TransactionTable, type Filter } from "./components/TransactionTable";
import { UploadPanel } from "./components/UploadPanel";
import type {
  ImportOptions,
  ReviewInput,
  Statement,
  StatementListItem,
  Transaction,
} from "./types";

type Page = "overview" | "transactions" | "statements" | "guide";
const pageTitles = {
  overview: "Overview",
  transactions: "Transactions",
  statements: "Statements",
  guide: "Import guide",
};
const errorText = (e: unknown) =>
  e instanceof Error ? e.message : "Something went wrong. Please try again.";

export default function App() {
  const [page, setPage] = useState<Page>("overview");
  const [statements, setStatements] = useState<StatementListItem[]>([]);
  const [statement, setStatement] = useState<Statement | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [review, setReview] = useState<Transaction | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [category, setCategory] = useState("");
  const uploadDialog = useRef<HTMLDialogElement>(null);
  const loadVersion = useRef(0);

  useEffect(() => {
    void initialize();
  }, []);
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 6500);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    if (uploadOpen) uploadDialog.current?.showModal();
  }, [uploadOpen]);

  function selectStatement(result: Statement) {
    setStatement(result);
    try {
      localStorage.setItem("ledgerly.statement", result.id);
    } catch {
      /* Storage is optional. */
    }
    setFilter("all");
    setCategory("");
  }
  async function initialize() {
    setLoading(true);
    setError("");
    try {
      const list = await api.list();
      setStatements(list);
      let saved: string | null = null;
      try {
        saved = localStorage.getItem("ledgerly.statement");
      } catch {
        /* No persistence preference. */
      }
      const id = list.find((item) => item.id === saved)?.id || list[0]?.id;
      if (id) selectStatement(await api.get(id));
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }
  async function openStatement(id: string) {
    const version = ++loadVersion.current;
    setBusy(true);
    setError("");
    try {
      const result = await api.get(id);
      if (version === loadVersion.current) {
        selectStatement(result);
        setPage("overview");
      }
    } catch (e) {
      if (version === loadVersion.current) setError(errorText(e));
    } finally {
      if (version === loadVersion.current) setBusy(false);
    }
  }
  async function upload(file: File, options: ImportOptions) {
    setBusy(true);
    setError("");
    try {
      const result = await api.upload(file, options);
      selectStatement(result);
      setPage("overview");
      setUploadOpen(false);
      setToast(
        result.already_imported
          ? "Already imported. Your saved reviews are still here."
          : `${result.summary.transaction_count} transactions imported. Your statement is ready.`,
      );
      setStatements(await api.list());
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }
  async function demo() {
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/samples/freelancer_statement.csv");
      if (!response.ok)
        throw new Error("The sample could not be loaded. Please retry.");
      const file = new File(
        [await response.blob()],
        "freelancer_statement.csv",
        { type: "text/csv" },
      );
      await upload(file, {
        date_format: "ISO",
        currency: "USD",
        amount_convention: "negative_expense",
      });
    } catch (e) {
      setError(errorText(e));
      setBusy(false);
    }
  }
  async function saveReview(input: ReviewInput) {
    if (!statement || !review) return;
    const result = await api.review(statement.id, review.id, input);
    setStatement(result);
    setReview(null);
    setToast("Changes saved. Your totals are up to date.");
    setStatements((list) =>
      list.map((item) =>
        item.id === result.id
          ? { ...item, needs_review: result.summary.needs_review }
          : item,
      ),
    );
  }
  function reviewQueue() {
    setFilter("needs_review");
    setCategory("");
    setPage("transactions");
  }
  const pending = statement?.summary.needs_review || 0;
  const completed = statement
    ? Math.round((1 - pending / statement.summary.transaction_count) * 100)
    : 0;

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setPage("overview");
          }}
        >
          <span className="brand-mark">
            <span />
            <span />
          </span>
          ledgerly<span className="brand-period">.</span>
        </a>
        <div className="workspace">
          <div className="workspace-avatar">F</div>
          <div>
            <strong>Freelancer workspace</strong>
            <span>Make room for your best work</span>
          </div>
        </div>
        <p className="nav-label">YOUR WORKSPACE</p>
        <nav aria-label="Main navigation">
          {(
            [
              { key: "overview", icon: LayoutDashboard },
              { key: "transactions", icon: ListFilter },
              { key: "statements", icon: FolderOpen },
            ] as const
          ).map((item) => (
            <button
              key={item.key}
              className={`nav-item ${page === item.key ? "selected" : ""}`}
              aria-current={page === item.key ? "page" : undefined}
              onClick={() => setPage(item.key)}
            >
              <item.icon size={19} strokeWidth={1.7} />
              {pageTitles[item.key]}
              {item.key === "transactions" && pending > 0 && (
                <span className="nav-count">{pending}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="sidebar-tip">
            <Leaf size={23} strokeWidth={1.5} />
            <h3>
              Less sorting.
              <br />
              More creating.
            </h3>
            <p>
              Your work is personal.
              <br />
              Your books should make sense.
            </p>
          </div>
          <button
            className={`nav-item ${page === "guide" ? "selected" : ""}`}
            onClick={() => setPage("guide")}
          >
            <CircleHelp size={18} />
            Import guide
            <ArrowUpRight size={14} className="nav-trailing" />
          </button>
          <div className="local-indicator">
            <span />
            Local workspace <LockKeyhole size={12} />
          </div>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div>
            <span className="breadcrumb-root">Workspace</span>
            <ChevronRight size={13} />
            <strong>{pageTitles[page]}</strong>
          </div>
          <div>
            <span className="private-label">
              <ShieldCheck size={15} />
              Private by default
            </span>
            <span className="profile-avatar">FW</span>
          </div>
        </header>
        <main id="main-content">
          <div className="page-heading">
            <div>
              <p className="eyebrow">A LITTLE CLARITY FOR YOUR FINANCES</p>
              <h1>
                {page === "overview"
                  ? "Your books, a little clearer."
                  : pageTitles[page]}
              </h1>
              <p>
                {page === "overview"
                  ? "From a messy statement to an organized month. You’ve got this."
                  : page === "transactions"
                    ? "Understand every entry. Give the uncertain ones a second look."
                    : page === "statements"
                      ? "Your statements and saved reviews, all in one place."
                      : "A few simple details for a smooth import."}
              </p>
            </div>
            <button
              className="button primary"
              disabled={busy}
              onClick={() => {
                setError("");
                setUploadOpen(true);
              }}
            >
              <Plus size={17} />
              Upload statement
            </button>
          </div>

          {error && !uploadOpen && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button className="text-button" onClick={() => void initialize()}>
                Retry
              </button>
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {loading ? (
            <div className="loading-state">
              <LoaderCircle className="spin" size={28} />
              <p>Opening your workspace…</p>
            </div>
          ) : (
            <>
              {page === "guide" ? (
                <ImportGuide />
              ) : page === "statements" ? (
                <section className="panel statements-panel">
                  <div className="panel-title">
                    <div>
                      <h2>Statement library</h2>
                      <p>
                        {statements.length} saved{" "}
                        {statements.length === 1 ? "statement" : "statements"}
                      </p>
                    </div>
                    <FileClock size={22} />
                  </div>
                  {statements.length ? (
                    statements.map((item) => (
                      <button
                        key={item.id}
                        className="statement-item"
                        disabled={busy}
                        onClick={() => void openStatement(item.id)}
                      >
                        <div className="document-icon">
                          <FileSpreadsheet size={21} />
                        </div>
                        <div>
                          <strong>{item.filename}</strong>
                          <span>
                            {item.transaction_count} transactions ·{" "}
                            {item.currency} · Imported{" "}
                            {new Date(item.created_at).toLocaleDateString()}
                          </span>
                        </div>
                        <span
                          className={`library-status ${item.needs_review ? "pending" : ""}`}
                        >
                          {item.needs_review
                            ? `${item.needs_review} to review`
                            : "All categorized"}
                        </span>
                        <ChevronRight size={18} />
                      </button>
                    ))
                  ) : (
                    <div className="small-empty">
                      <FolderOpen size={32} />
                      <h3>A home for your statements</h3>
                      <p>
                        Upload your first CSV or explore the sample to get
                        started.
                      </p>
                      <button
                        className="button primary"
                        onClick={() => setUploadOpen(true)}
                      >
                        Upload a statement
                      </button>
                    </div>
                  )}
                </section>
              ) : !statement ? (
                <>
                  <div className="welcome-banner">
                    <div>
                      <span className="welcome-tag">
                        <Sparkles size={13} /> SMALL STEPS. CLEARER BOOKS.
                      </span>
                      <h2>
                        Goodbye, spreadsheet overwhelm.
                        <br />
                        <em>Hello, a little more headspace.</em>
                      </h2>
                      <p>
                        Bring your statement. We’ll sort the familiar, flag the
                        uncertain,
                        <br className="desktop-break" /> and help you finish
                        with confidence.
                      </p>
                      <div className="welcome-points">
                        <span>
                          <Check size={15} />
                          No bank connection
                        </span>
                        <span>
                          <Check size={15} />
                          You’re always in control
                        </span>
                      </div>
                    </div>
                    <LedgerIllustration />
                  </div>
                  <div className="onboarding-grid">
                    <section className="panel">
                      <div className="panel-title">
                        <div>
                          <h2>Start with your statement</h2>
                          <p>One CSV. A much clearer picture.</p>
                        </div>
                        <span className="step-badge">01</span>
                      </div>
                      <UploadPanel
                        onUpload={(file, options) => void upload(file, options)}
                        busy={busy}
                        onDemo={() => void demo()}
                      />
                    </section>
                    <section className="how-it-works">
                      <p className="eyebrow">YOUR MONTH, SORTED</p>
                      <h2>
                        Three steps to
                        <br />a lighter workload.
                      </h2>
                      {[
                        [
                          "01",
                          "Bring it all together",
                          "Upload a CSV export of your bank or credit card transactions.",
                        ],
                        [
                          "02",
                          "Let the familiar fall into place",
                          "Known merchants get a category, with a clear explanation of why.",
                        ],
                        [
                          "03",
                          "Add your final say",
                          "Review anything uncertain, then export your organized statement.",
                        ],
                      ].map(([n, title, description]) => (
                        <div className="how-step" key={n}>
                          <span>{n}</span>
                          <div>
                            <h3>{title}</h3>
                            <p>{description}</p>
                          </div>
                        </div>
                      ))}
                      <div className="honest-note">
                        <BookOpen size={18} />
                        <p>
                          No mystery decisions. Every category has a reason you
                          can inspect and change.
                        </p>
                      </div>
                    </section>
                  </div>
                </>
              ) : (
                <>
                  <div className="statement-context">
                    <div>
                      <span className="document-icon">
                        <FileSpreadsheet size={18} />
                      </span>
                      <label className="sr-only" htmlFor="active-statement">
                        Active statement
                      </label>
                      <select
                        id="active-statement"
                        value={statement.id}
                        disabled={busy}
                        onChange={(e) => void openStatement(e.target.value)}
                      >
                        {statements.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.filename}
                          </option>
                        ))}
                      </select>
                      <span className="statement-period">
                        {shortDate(statement.date_from)} –{" "}
                        {shortDate(statement.date_to)},{" "}
                        {statement.date_to.slice(0, 4)}
                      </span>
                      <span className="currency-label">
                        {statement.currency}
                      </span>
                    </div>
                    <a
                      className="button secondary export-button"
                      href={`/api/statements/${statement.id}/export`}
                      download
                    >
                      <Download size={15} />
                      Export CSV
                    </a>
                  </div>
                  {page === "overview" && (
                    <>
                      <SummaryCards statement={statement} />
                      <div className="overview-grid">
                        <CategoryBreakdown
                          statement={statement}
                          onCategory={(selected) => {
                            setCategory(selected);
                            setFilter("all");
                            setPage("transactions");
                          }}
                        />
                        <section
                          className={`review-card ${!pending ? "complete" : ""}`}
                        >
                          <div className="review-card-top">
                            <span className="eyebrow">THE FINISHING TOUCH</span>
                            <CheckCheck size={23} />
                          </div>
                          <h2>
                            {pending ? (
                              <>
                                A little review.
                                <br />A lot more clarity.
                              </>
                            ) : (
                              <>
                                All sorted.
                                <br />
                                Nicely done.
                              </>
                            )}
                          </h2>
                          <p>
                            {pending
                              ? `${pending} ${pending === 1 ? "transaction needs" : "transactions need"} your judgment. We’ve set them aside so your totals stay honest.`
                              : "Every transaction has a category. Take one last look, then export your organized statement."}
                          </p>
                          <div className="review-progress">
                            <div>
                              <span>Statement categorized</span>
                              <strong>{completed}%</strong>
                            </div>
                            <div className="progress-track">
                              <span style={{ width: `${completed}%` }} />
                            </div>
                          </div>
                          {pending > 0 && (
                            <p className="pending-amounts">
                              Awaiting review:{" "}
                              {money(
                                statement.summary.pending_outflow_cents,
                                statement.currency,
                              )}{" "}
                              out ·{" "}
                              {money(
                                statement.summary.pending_inflow_cents,
                                statement.currency,
                              )}{" "}
                              in
                            </p>
                          )}
                          <button
                            className="button review-cta"
                            onClick={
                              pending
                                ? reviewQueue
                                : () => setPage("transactions")
                            }
                          >
                            {pending
                              ? "Let’s review them"
                              : "View transactions"}
                            <ArrowRight size={17} />
                          </button>
                        </section>
                      </div>
                    </>
                  )}
                  <TransactionTable
                    key={statement.id}
                    statement={statement}
                    onReview={setReview}
                    filter={filter}
                    setFilter={setFilter}
                    category={category}
                    setCategory={setCategory}
                  />
                  {statement.summary.needs_review > 0 && (
                    <p className="export-note">
                      <InfoIcon />
                      Exports include pending rows marked “needs_review”; totals
                      above exclude them.
                    </p>
                  )}
                </>
              )}
            </>
          )}
          <footer className="page-footer">
            <span>
              <Leaf size={14} />A little order goes a long way.
            </span>
            <span>Ledgerly · Made for independent work</span>
          </footer>
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <Check size={18} />
          <span>{toast}</span>
          <button
            className="icon-button"
            aria-label="Dismiss notification"
            onClick={() => setToast("")}
          >
            <X size={16} />
          </button>
        </div>
      )}
      {uploadOpen && (
        <dialog
          ref={uploadDialog}
          className="modal upload-modal"
          aria-labelledby="upload-title"
          onCancel={(e) => {
            e.preventDefault();
            if (!busy) setUploadOpen(false);
          }}
        >
          <div className="modal-heading">
            <div>
              <p className="eyebrow">A NEW CHAPTER</p>
              <h2 id="upload-title">Bring your statement.</h2>
            </div>
            <button
              className="icon-button"
              disabled={busy}
              aria-label="Close upload"
              onClick={() => {
                setUploadOpen(false);
                setError("");
              }}
            >
              <X size={20} />
            </button>
          </div>
          {error && (
            <p className="error-message" role="alert">
              {error}
            </p>
          )}
          <UploadPanel
            onUpload={(file, options) => void upload(file, options)}
            busy={busy}
            onDemo={() => void demo()}
          />
        </dialog>
      )}
      {review && statement && (
        <ReviewDialog
          row={review}
          currency={statement.currency}
          onClose={() => setReview(null)}
          onSave={saveReview}
        />
      )}
    </div>
  );
}

function InfoIcon() {
  return <CircleHelp size={14} />;
}
function LedgerIllustration() {
  return (
    <div className="ledger-illustration" aria-hidden="true">
      <span className="orbit orbit-one" />
      <span className="orbit orbit-two" />
      <div className="paper-back" />
      <div className="paper-front">
        <div className="paper-heading">
          <span>YOUR MONTH</span>
          <Leaf size={19} />
        </div>
        <div className="paper-rule" />
        <div className="paper-line">
          <span /> <i />
        </div>
        <div className="paper-line">
          <span /> <i />
        </div>
        <div className="paper-line">
          <span /> <i />
        </div>
        <div className="paper-total">
          <span>All in order.</span>
          <Check size={16} />
        </div>
      </div>
      <div className="floating-check">
        <Check size={25} />
      </div>
      <span className="illustration-spark">✳</span>
    </div>
  );
}

function ImportGuide() {
  return (
    <div className="guide-grid">
      <section className="panel guide-panel">
        <FileSpreadsheet size={25} />
        <h2>A simple format. A smooth start.</h2>
        <p>
          Upload a UTF-8, comma-separated CSV with these columns. Amounts use a
          dot for decimals.
        </p>
        <div className="code-sample">
          <code>
            date,description,amount,currency
            <br />
            2026-10-01,ADOBE CREATIVE CLOUD,-59.99,USD
            <br />
            2026-10-02,ADOBE REFUND,10.00,USD
          </code>
        </div>
        <dl className="guide-definitions">
          <dt>Required</dt>
          <dd>
            <code>date</code>, <code>description</code>, and <code>amount</code>{" "}
            — or separate <code>debit</code> and <code>credit</code> columns.
          </dd>
          <dt>Optional</dt>
          <dd>
            <code>transaction_id</code> and <code>currency</code>. Choose the
            currency during upload if it is missing.
          </dd>
          <dt>Date format</dt>
          <dd>
            Choose YYYY-MM-DD, DD/MM/YYYY, or MM/DD/YYYY to match your entire
            file. We never guess ambiguous dates.
          </dd>
          <dt>Amount direction</dt>
          <dd>
            By default, negative means spending. Select the opposite convention
            if your card export uses positive charges. Debit/credit columns
            always use positive values.
          </dd>
          <dt>Supported currencies</dt>
          <dd>
            USD, PKR, EUR, GBP, CAD and AUD. One currency per file, with at most
            two decimal places.
          </dd>
          <dt>Common bank headings</dt>
          <dd>
            Transaction Date / Posting Date → date; Details / Narration / Memo →
            description; Withdrawal / Deposit → debit / credit.
          </dd>
        </dl>
        <div className="button-row">
          <a
            className="button primary"
            href="/api/samples/freelancer_statement.csv"
            download
          >
            <Download size={16} />
            Download sample
          </a>
          <a
            className="button secondary"
            href="/api/samples/debit_credit_statement.csv"
            download
          >
            Debit/credit sample
          </a>
        </div>
      </section>
      <section className="panel guide-panel">
        <ShieldCheck size={25} />
        <h2>You have the final say.</h2>
        <p>
          Ledgerly uses explicit merchant and transaction rules for a freelance
          design business. It asks for help whenever a decision is uncertain.
        </p>
        <ul className="guide-list">
          <li>Refunds reduce expenses; they aren’t client income.</li>
          <li>Transfers and card payments are kept out of expense totals.</li>
          <li>
            Possible duplicate rows stay visible and await your confirmation.
          </li>
          <li>
            Unknown deposits, cafés, fuel stations and general marketplaces need
            review.
          </li>
          <li>
            Invalid files show a row error. Nothing is partially imported.
          </li>
          <li>
            Re-importing an identical file with the same options opens your
            saved version.
          </li>
        </ul>
        <div className="honest-note">
          <LockKeyhole size={18} />
          <p>
            Your data stays in a database on this computer. Use fictional data
            only for the assessment.
          </p>
        </div>
        <p className="subtle-note">
          Categories organize your records. They do not determine tax
          deductibility. PDF, XLSX, scanned documents and currency conversion
          are outside this version’s scope.
        </p>
      </section>
    </div>
  );
}
