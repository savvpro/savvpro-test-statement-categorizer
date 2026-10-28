"use client";

import { ChangeEvent, DragEvent, useMemo, useRef, useState } from "react";

const CATEGORIES = [
  "Needs review",
  "Advertising",
  "Bank fees",
  "Income",
  "Meals",
  "Office supplies",
  "Professional services",
  "Refund",
  "Software",
  "Transfer",
  "Travel",
  "Utilities",
] as const;

const EXPENSE_CATEGORIES = new Set<string>([
  "Advertising",
  "Bank fees",
  "Meals",
  "Office supplies",
  "Professional services",
  "Software",
  "Travel",
  "Utilities",
]);

type Category = (typeof CATEGORIES)[number];
type TransactionStatus = "categorized" | "review" | "reviewed";

type Transaction = {
  id: string;
  date: string;
  description: string;
  amount: number;
  category: Category;
  status: TransactionStatus;
  confidence: number;
  reason: string;
};

const SAMPLE_TRANSACTIONS: Transaction[] = [
  { id: "demo-1", date: "2026-10-18", description: "ADOBE CREATIVE CLOUD", amount: -59.99, category: "Software", status: "categorized", confidence: 0.96, reason: "Matched a known software merchant." },
  { id: "demo-2", date: "2026-10-17", description: "UBER TRIP", amount: -24.5, category: "Travel", status: "categorized", confidence: 0.96, reason: "Matched a known travel merchant." },
  { id: "demo-3", date: "2026-10-16", description: "JOES CAFE 9921", amount: -18, category: "Needs review", status: "review", confidence: 0, reason: "No specific rule matched. Confirm the merchant and business purpose before assigning a category." },
  { id: "demo-4", date: "2026-10-15", description: "TRANSFER TO SAVINGS", amount: -350, category: "Transfer", status: "categorized", confidence: 0.96, reason: "Matched a known transfer phrase." },
  { id: "demo-5", date: "2026-10-14", description: "FIGMA INC", amount: -16, category: "Software", status: "categorized", confidence: 0.96, reason: "Matched a known software merchant." },
  { id: "demo-6", date: "2026-10-12", description: "DELTA AIR LINES", amount: -286.4, category: "Travel", status: "categorized", confidence: 0.96, reason: "Matched a known travel merchant." },
  { id: "demo-7", date: "2026-10-10", description: "CLIENT PAYMENT ACME STUDIO", amount: 1800, category: "Income", status: "categorized", confidence: 0.96, reason: "Matched a known client-income phrase." },
  { id: "demo-8", date: "2026-10-08", description: "ADOBE REFUND", amount: 14.99, category: "Refund", status: "categorized", confidence: 0.96, reason: "Matched a known refund phrase." },
  { id: "demo-9", date: "2026-10-05", description: "STAPLES STORE 0482", amount: -42.75, category: "Office supplies", status: "categorized", confidence: 0.96, reason: "Matched a known office supplies merchant." },
  { id: "demo-10", date: "2026-10-03", description: "STARBUCKS STORE 1044", amount: -12.4, category: "Meals", status: "categorized", confidence: 0.96, reason: "Matched a known meals merchant. Confirm business purpose." },
];

type CategorizeResponse = {
  filename: string;
  transactions: Transaction[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function formatCurrency(amount: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(amount);
}

function formatDate(date: string) {
  const parsed = new Date(`${date.slice(0, 10)}T12:00:00`);
  return Number.isNaN(parsed.getTime())
    ? date
    : new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      }).format(parsed);
}

function initials(description: string) {
  return description
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();
}

export default function Home() {
  const [transactions, setTransactions] = useState(SAMPLE_TRANSACTIONS);
  const [filename, setFilename] = useState("October sample statement");
  const [filter, setFilter] = useState<"all" | "review">("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const reviewCount = transactions.filter((item) => item.status === "review").length;
  const reviewedCount = transactions.length - reviewCount;
  const deductibleSpend = transactions.reduce((total, item) => {
    if (item.amount < 0 && EXPENSE_CATEGORIES.has(item.category)) {
      return total + Math.abs(item.amount);
    }
    return total;
  }, 0);

  const categoryTotals = useMemo(() => {
    return transactions.reduce<Record<string, number>>((totals, item) => {
      if (item.amount < 0 && EXPENSE_CATEGORIES.has(item.category)) {
        totals[item.category] = (totals[item.category] ?? 0) + Math.abs(item.amount);
      }
      return totals;
    }, {});
  }, [transactions]);

  const visibleTransactions = transactions.filter((item) => {
    const matchesFilter = filter === "all" || item.status === "review";
    const matchesSearch = item.description.toLowerCase().includes(search.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  async function uploadStatement(file: File) {
    setError("");
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please choose a CSV statement. PDF and image files are not supported yet.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    setIsLoading(true);
    try {
      const response = await fetch(`${apiUrl}/api/categorize`, {
        method: "POST",
        body: formData,
      });
      const payload = (await response.json()) as CategorizeResponse | { detail?: string };
      if (!response.ok) {
        throw new Error(
          "detail" in payload && payload.detail
            ? payload.detail
            : "We could not read this statement. Check its format and try again.",
        );
      }

      const result = payload as CategorizeResponse;
      setTransactions(result.transactions);
      setFilename(result.filename);
      setFilter("all");
      setSearch("");
    } catch (uploadError) {
      setError(
        uploadError instanceof TypeError
          ? "Could not reach the categorizer. Make sure the backend is running at the configured API address."
          : uploadError instanceof Error
            ? uploadError.message
            : "The statement could not be processed.",
      );
    } finally {
      setIsLoading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    if (file) void uploadStatement(file);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setIsDragging(false);
    const file = event.dataTransfer.files[0];
    if (file) void uploadStatement(file);
  }

  function changeCategory(id: string, category: Category) {
    setTransactions((current) =>
      current.map((item) =>
        item.id === id
          ? { ...item, category, status: "reviewed" }
          : item,
      ),
    );
  }

  function exportTransactions() {
    if (!transactions.length) return;
    const escapeCell = (value: string | number) =>
      `"${String(value).replaceAll('"', '""')}"`;
    const rows = [
      ["Date", "Description", "Amount", "Category", "Status"],
      ...transactions.map((item) => [
        item.date,
        item.description,
        item.amount.toFixed(2),
        item.category,
        item.status,
      ]),
    ];
    const csv = rows.map((row) => row.map(escapeCell).join(",")).join("\r\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "freelance-ledger-reviewed.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview" aria-label="Freelance Ledger home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none">
              <rect x="3" y="4" width="26" height="24" rx="8" fill="currentColor" />
              <path d="M10 11h12M10 16h8M10 21h5" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <circle cx="23" cy="21" r="2" fill="#C7F36B" />
            </svg>
          </span>
          <span className="brand-name">freelance<span>ledger</span></span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          <a className="nav-link active" href="#overview">
            <span className="nav-icon" aria-hidden="true">◫</span>
            Overview
          </a>
          <a className="nav-link" href="#transactions">
            <span className="nav-icon" aria-hidden="true">≡</span>
            Transactions
            {reviewCount > 0 && <span className="nav-count">{reviewCount}</span>}
          </a>
          <a className="nav-link" href="#how-it-works">
            <span className="nav-icon" aria-hidden="true">✳</span>
            How it works
          </a>
        </nav>

        <div className="sidebar-bottom">
          <div className="privacy-card">
            <span className="privacy-icon" aria-hidden="true">⌑</span>
            <strong>Your data stays yours</strong>
            <p>Statements are processed in memory and never saved.</p>
          </div>
          <div className="profile">
            <div className="profile-avatar">FD</div>
            <div className="profile-copy">
              <strong>Freelance designer</strong>
              <span>Personal workspace</span>
            </div>
            <span className="profile-dots" aria-hidden="true">···</span>
          </div>
        </div>
      </aside>

      <section className="main-panel" id="overview">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> Overview</div>
          <div className="top-actions">
            <span className="secure-label"><span aria-hidden="true">●</span> Private workspace</span>
            <button className="button button-secondary export-button" onClick={exportTransactions}>
              <span aria-hidden="true">↓</span> Export CSV
            </button>
            <button className="button button-primary" onClick={() => fileInput.current?.click()} disabled={isLoading}>
              <span aria-hidden="true">＋</span> Upload statement
            </button>
          </div>
        </header>

        <div className="dashboard">
          <section className="intro">
            <div>
              <div className="eyebrow"><span className="eyebrow-dot" /> YOUR MONEY, MORE ORGANIZED</div>
              <h1>Good work deserves<br />a <em>clearer</em> picture.</h1>
              <p>Review your business spending and get tax-time ready, one transaction at a time.</p>
            </div>
            <div className="intro-art" aria-hidden="true">
              <div className="art-orbit orbit-one" />
              <div className="art-orbit orbit-two" />
              <div className="art-sun" />
              <div className="art-leaf leaf-one" />
              <div className="art-leaf leaf-two" />
              <div className="art-card"><span /><span /><span /></div>
              <div className="art-sparkle sparkle-one">✳</div>
              <div className="art-sparkle sparkle-two">✳</div>
            </div>
          </section>

          <section className="stats-grid" aria-label="Statement summary">
            <article className="stat-card stat-primary">
              <div className="stat-heading"><span>REVIEWED BUSINESS SPEND</span><span className="stat-icon green-icon">↗</span></div>
              <div className="stat-value">{formatCurrency(deductibleSpend)}</div>
              <div className="stat-foot"><span className="tiny-indicator green-indicator" /> Across {transactions.length} transactions</div>
              <div className="stat-decoration" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></div>
            </article>
            <article className="stat-card">
              <div className="stat-heading"><span>NEEDS YOUR EYES</span><span className="stat-icon amber-icon">◎</span></div>
              <div className="stat-value">{String(reviewCount).padStart(2, "0")}<small> transactions</small></div>
              <button className="text-action" onClick={() => { setFilter("review"); document.getElementById("transactions")?.scrollIntoView({ behavior: "smooth" }); }}>
                Review flagged items <span aria-hidden="true">→</span>
              </button>
            </article>
            <article className="stat-card">
              <div className="stat-heading"><span>STATEMENT PROGRESS</span><span className="stat-icon blue-icon">✓</span></div>
              <div className="stat-value">{transactions.length ? Math.round((reviewedCount / transactions.length) * 100) : 0}<small>% sorted</small></div>
              <div className="progress-track"><span style={{ width: `${transactions.length ? (reviewedCount / transactions.length) * 100 : 0}%` }} /></div>
              <div className="stat-foot">{reviewedCount} of {transactions.length} categorized</div>
            </article>
          </section>

          <section
            className={`upload-strip${isDragging ? " drag-active" : ""}`}
            onDragOver={(event) => { event.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            aria-label="Upload a bank statement"
          >
            <div className="upload-icon" aria-hidden="true">
              {isLoading ? <span className="spinner" /> : <svg viewBox="0 0 24 24" fill="none"><path d="M12 16V4m0 0L7 9m5-5 5 5M5 15v4a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-4" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" /></svg>}
            </div>
            <div className="upload-copy">
              <strong>{isLoading ? "Reading your statement…" : "Drop a statement to get started"}</strong>
              <span>{isLoading ? "Applying your personal categorization rules" : "Bring in a CSV from your bank. We’ll sort the knowns and flag the maybes."}</span>
            </div>
            <button className="button button-outline" onClick={() => fileInput.current?.click()} disabled={isLoading}>
              Browse files
            </button>
            <input ref={fileInput} className="visually-hidden" type="file" accept=".csv,text/csv" onChange={handleFileChange} aria-label="Choose a CSV statement" />
          </section>
          {error && <div className="error-banner" role="alert"><span>!</span>{error}</div>}

          <section className="content-grid">
            <div className="transactions-panel" id="transactions">
              <div className="section-heading">
                <div>
                  <div className="section-kicker">YOUR BOOKS, AT A GLANCE</div>
                  <h2>Transactions <span className="heading-count">{transactions.length}</span></h2>
                </div>
                <button className="subtle-button" onClick={() => { setTransactions(SAMPLE_TRANSACTIONS); setFilename("October sample statement"); setFilter("all"); setSearch(""); setError(""); }}>
                  <span aria-hidden="true">↻</span> Load sample
                </button>
              </div>

              <div className="table-toolbar">
                <div className="filter-tabs" role="group" aria-label="Filter transactions">
                  <button className={filter === "all" ? "filter-tab selected" : "filter-tab"} onClick={() => setFilter("all")}>All transactions</button>
                  <button className={filter === "review" ? "filter-tab selected" : "filter-tab"} onClick={() => setFilter("review")}>
                    Needs review {reviewCount > 0 && <span className="filter-badge">{reviewCount}</span>}
                  </button>
                </div>
                <label className="search-field">
                  <span aria-hidden="true">⌕</span>
                  <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search transactions" aria-label="Search transactions" />
                  <kbd>⌘ K</kbd>
                </label>
              </div>

              <div className="table-caption">
                <span>{filename}</span>
                <span>{visibleTransactions.length} transactions</span>
              </div>
              <div className="transaction-table-wrap">
                <table className="transaction-table">
                  <thead>
                    <tr>
                      <th scope="col">DATE</th>
                      <th scope="col">MERCHANT</th>
                      <th scope="col">CATEGORY</th>
                      <th scope="col" className="amount-heading">AMOUNT</th>
                      <th scope="col">STATUS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibleTransactions.map((item) => (
                      <tr key={item.id} className={item.status === "review" ? "review-row" : ""}>
                        <td className="date-cell">{formatDate(item.date)}</td>
                        <td>
                          <div className="merchant-cell">
                            <span className={`merchant-avatar avatar-${item.category.toLowerCase().replaceAll(" ", "-")}`}>{initials(item.description)}</span>
                            <span className="merchant-copy">
                              <strong>{item.description}</strong>
                              {item.status === "review" && <small title={item.reason}>No rule matched · confirm business purpose</small>}
                            </span>
                          </div>
                        </td>
                        <td>
                          <label className="category-select-wrap">
                            <span className={`category-dot dot-${item.category.toLowerCase().replaceAll(" ", "-")}`} />
                            <select
                              aria-label={`Category for ${item.description}`}
                              className={`category-select${item.status === "review" ? " needs-review" : ""}`}
                              value={item.category}
                              onChange={(event) => changeCategory(item.id, event.currentTarget.value as Category)}
                            >
                              {CATEGORIES.map((category) => <option key={category} value={category}>{category}</option>)}
                            </select>
                            <span className="select-chevron" aria-hidden="true">⌄</span>
                          </label>
                        </td>
                        <td className={`amount-cell${item.amount > 0 ? " positive-amount" : ""}`}>{formatCurrency(item.amount)}</td>
                        <td>
                          <span className={`status-pill status-${item.status}`}>
                            <span />{item.status === "review" ? "Review" : item.status === "reviewed" ? "Edited" : "Sorted"}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {visibleTransactions.length === 0 && (
                      <tr><td className="empty-state" colSpan={5}>{filter === "review" ? "You’re all caught up. No transactions need review." : "No transactions match this search."}</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
              <div className="table-footer">
                <span>Showing {visibleTransactions.length} of {transactions.length} transactions</span>
                <button className="footer-link" onClick={exportTransactions}>Download report <span aria-hidden="true">↗</span></button>
              </div>
            </div>

            <aside className="insights-column">
              <section className="category-card">
                <div className="side-card-heading">
                  <div><div className="section-kicker">WHERE IT GOES</div><h3>Spending by category</h3></div>
                  <span className="more-button" aria-hidden="true">···</span>
                </div>
                <div className="category-total">{formatCurrency(deductibleSpend)}<span> total business spend</span></div>
                <div className="category-bars" aria-label="Business spending by category">
                  {Object.entries(categoryTotals).sort(([, a], [, b]) => b - a).slice(0, 5).map(([category, total], index) => (
                    <div className="bar-row" key={category}>
                      <div className="bar-label"><span className={`bar-dot bar-color-${index}`} />{category}<strong>{formatCurrency(total)}</strong></div>
                      <div className="bar-track"><span className={`bar-fill bar-color-${index}`} style={{ width: `${deductibleSpend ? (total / deductibleSpend) * 100 : 0}%` }} /></div>
                    </div>
                  ))}
                  {Object.keys(categoryTotals).length === 0 && <div className="no-spending">Upload a statement to see category totals.</div>}
                </div>
                <div className="category-note"><span aria-hidden="true">✳</span> Figures are for organization, not tax advice.</div>
              </section>

              <section className="tip-card" id="how-it-works">
                <div className="tip-icon" aria-hidden="true">✳</div>
                <div className="section-kicker">A LITTLE REMINDER</div>
                <h3>Not sure? That’s what review is for.</h3>
                <p>We only sort transactions when a specific rule matches. Anything uncertain stays in your hands.</p>
                <button className="tip-link" onClick={() => { setFilter("review"); document.getElementById("transactions")?.scrollIntoView({ behavior: "smooth" }); }}>
                  See what needs a look <span aria-hidden="true">→</span>
                </button>
              </section>
            </aside>
          </section>

          <footer className="page-footer">
            <span>Made for the people who make things.</span>
            <span><span className="footer-dot" /> Your statements are never stored</span>
          </footer>
        </div>
      </section>
    </main>
  );
}
