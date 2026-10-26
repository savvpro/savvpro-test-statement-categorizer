import { useMemo, useRef, useState } from "react";
import { ArrowDownToLine, ArrowUpRight, Check, ChevronDown, CircleHelp, FileSpreadsheet, Filter, FolderOpen, RefreshCw, RotateCcw, Search, ShieldCheck, Sparkles, Upload, X } from "lucide-react";
import { CATEGORIES, type Category, type Transaction } from "@/lib/categorizer";
import { exportStatementCsv, parseStatementCsv } from "@/lib/csv";

const DEMO_CSV = `Date,Description,Amount,Type,Reference
2026-01-03,ADOBE CREATIVE CLOUD,-59.99,Debit,DEMO-001
2026-01-05,UBER *TRIP,-28.40,Debit,DEMO-002
2026-01-07,TRANSFER TO SAVINGS,-400.00,Debit,DEMO-003
2026-01-09,CLIENT PAYMENT - NORTHSTAR,+1200.00,Credit,DEMO-004
2026-01-11,JOES CAFE 9921,-18.75,Debit,DEMO-005
2026-01-12,FIGMA PROFESSIONAL,-15.00,Debit,DEMO-006
2026-01-15,REFUND - AIRTABLE,+24.00,Credit,DEMO-007
2026-01-17,MONTHLY SERVICE FEE,-12.00,Debit,DEMO-008
2026-01-19,STAPLES OFFICE SUPPLIES,-43.22,Debit,DEMO-009
2026-01-22,META ADS CAMPAIGN,-80.00,Debit,DEMO-010
2026-01-24,APPLE STORE MONITOR,-249.00,Debit,DEMO-011
2026-01-26,PROJECT DEPOSIT - LUMEN,+850.00,Credit,DEMO-012`;

const categoryColors: Record<string, string> = {
  Software: "teal",
  Travel: "sky",
  Meals: "amber",
  "Office supplies": "violet",
  Equipment: "indigo",
  Advertising: "pink",
  "Bank fees": "slate",
  Refund: "emerald",
  Income: "emerald",
  "Transfer / non-spend": "stone",
  "Needs review": "clay",
};

const spendingCategories: Category[] = ["Software", "Travel", "Meals", "Office supplies", "Equipment", "Advertising", "Bank fees"];

function demoResult() {
  const parsed = parseStatementCsv(DEMO_CSV);
  return { transactions: parsed.transactions, headers: parsed.headers };
}

function formatMoney(amount: number | null) {
  if (amount === null) return "—";
  const absolute = Math.abs(amount).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `${amount >= 0 ? "+" : "−"}PKR ${absolute}`;
}

function formatDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value || "No date";
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function categoryClass(category: string) {
  return `category-pill category-${categoryColors[category] ?? "stone"}`;
}

function StatusPill({ transaction }: { transaction: Transaction }) {
  if (transaction.status === "reviewed") {
    return <span className="status-pill status-reviewed"><Check size={12} /> reviewed</span>;
  }
  if (transaction.status === "needs_review") {
    return <span className="status-pill status-review"><CircleHelp size={12} /> needs review</span>;
  }
  return <span className="status-pill status-auto"><ShieldCheck size={12} /> rule matched</span>;
}

function StatCard({ label, value, note, tone = "default" }: { label: string; value: string; note: string; tone?: string }) {
  return <article className={`stat-card stat-${tone}`}>
    <div className="stat-label">{label}</div>
    <div className="stat-value">{value}</div>
    <div className="stat-note">{note}</div>
  </article>;
}

export default function Home() {
  const initial = useMemo(() => demoResult(), []);
  const [transactions, setTransactions] = useState<Transaction[]>(initial.transactions);
  const [headers, setHeaders] = useState<string[]>(initial.headers);
  const [fileName, setFileName] = useState("demo_statement.csv");
  const [activeFilter, setActiveFilter] = useState<"all" | "needs_review" | "categorized" | "reviewed">("all");
  const [categoryFilter, setCategoryFilter] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [batchCategory, setBatchCategory] = useState<Category>("Software");
  const [selectedReviewIds, setSelectedReviewIds] = useState<string[]>([]);
  const [draftCategories, setDraftCategories] = useState<Record<string, Category>>({});
  const [issues, setIssues] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const summary = useMemo(() => {
    const auto = transactions.filter((item) => item.status === "categorized").length;
    const review = transactions.filter((item) => item.status === "needs_review").length;
    const reviewed = transactions.filter((item) => item.status === "reviewed").length;
    const spend = transactions.reduce((total, item) => {
      if ((item.amount ?? 0) < 0 && item.category !== "Transfer / non-spend") return total + Math.abs(item.amount ?? 0);
      return total;
    }, 0);
    const coverage = transactions.length ? Math.round(((auto + reviewed) / transactions.length) * 100) : 0;
    return { auto, review, reviewed, spend, coverage };
  }, [transactions]);

  const categoryTotals = useMemo(() => spendingCategories.map((category) => ({
    category,
    total: transactions.filter((item) => item.category === category).reduce((sum, item) => sum + Math.abs(item.amount ?? 0), 0),
  })).filter((item) => item.total > 0).sort((a, b) => b.total - a.total), [transactions]);

  const reviewRows = transactions.filter((item) => item.status === "needs_review");
  const visibleRows = transactions.filter((item) => {
    const matchesStatus = activeFilter === "all" || item.status === activeFilter;
    const matchesCategory = !categoryFilter || item.category === categoryFilter;
    const haystack = `${item.description} ${item.date} ${item.category}`.toLowerCase();
    return matchesStatus && matchesCategory && haystack.includes(query.toLowerCase());
  });

  function replaceWithCsv(text: string, name: string) {
    try {
      const parsed = parseStatementCsv(text);
      setTransactions(parsed.transactions);
      setHeaders(parsed.headers);
      setFileName(name);
      setIssues(parsed.issues);
      setActiveFilter("all");
      setCategoryFilter(null);
      setSelectedReviewIds([]);
      setDraftCategories({});
    } catch (error) {
      setIssues([error instanceof Error ? error.message : "Could not read this CSV."]);
    }
  }

  function handleFile(file?: File) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setIssues(["simplke reads CSV statements. Export your statement as CSV and try again."]);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => replaceWithCsv(String(reader.result ?? ""), file.name);
    reader.onerror = () => setIssues(["The file could not be read. Try exporting it again as CSV."]);
    reader.readAsText(file);
  }

  function resetDemo() {
    const demo = demoResult();
    setTransactions(demo.transactions);
    setHeaders(demo.headers);
    setFileName("demo_statement.csv");
    setIssues([]);
    setActiveFilter("all");
    setCategoryFilter(null);
    setSelectedReviewIds([]);
    setDraftCategories({});
  }

  function selectReview(id: string) {
    setSelectedReviewIds((current) => current.includes(id) ? current.filter((item) => item !== id) : [...current, id]);
  }

  function updateDraft(id: string, value: Category) {
    setDraftCategories((current) => ({ ...current, [id]: value }));
  }

  function applyReview(ids: string[], fallbackCategory?: Category) {
    setTransactions((current) => current.map((item) => {
      if (!ids.includes(item.id)) return item;
      const category = draftCategories[item.id] ?? fallbackCategory ?? "Needs review";
      return { ...item, category, status: "reviewed", confidence: "review", ruleId: "user-review", ruleLabel: "User assigned category during review", reviewReason: undefined };
    }));
    setSelectedReviewIds([]);
  }

  function downloadExport() {
    const csv = exportStatementCsv(transactions, headers);
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${fileName.replace(/\.csv$/i, "")}-categorized.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand-lockup">
        <div className="brand-mark"><span>L</span><span>L</span></div>
        <div><div className="brand-name">simplke</div><div className="brand-subtitle">tax-time clarity</div></div>
      </div>
      <div className="sidebar-section-label">Workspace</div>
      <nav className="sidebar-nav" aria-label="Workspace navigation">
        <button className="nav-item nav-active"><FileSpreadsheet size={17} /><span>Statement review</span><span className="nav-count">{summary.review || "—"}</span></button>
        <button className="nav-item" onClick={() => setActiveFilter("categorized")}><ShieldCheck size={17} /><span>Auto-categorized</span><span className="nav-count">{summary.auto}</span></button>
        <button className="nav-item" onClick={() => setActiveFilter("reviewed")}><Check size={17} /><span>Reviewed by me</span><span className="nav-count">{summary.reviewed}</span></button>
      </nav>
      <div className="sidebar-bottom">
        <div className="rule-status"><div className="rule-status-icon"><Sparkles size={15} /></div><div><div className="rule-status-title">Your rules are active</div><div className="rule-status-copy">Deterministic · no AI guesses</div></div></div>
        <div className="sidebar-footer">Freelance designer workspace<br /><span>Business card · synthetic demo</span></div>
      </div>
    </aside>

    <main className="workspace">
      <header className="topbar">
        <div><div className="eyebrow">Statement workspace <span className="eyebrow-dot" /> January 2026</div><h1>Make this statement tax-ready.</h1></div>
        <div className="topbar-actions"><button className="button button-quiet" onClick={resetDemo}><RotateCcw size={15} /> Reset demo</button><button className="button button-primary" onClick={downloadExport}><ArrowDownToLine size={16} /> Export ledger</button></div>
      </header>

      <section className="import-strip" onDragEnter={() => setIsDragging(true)} onDragLeave={() => setIsDragging(false)} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); setIsDragging(false); handleFile(event.dataTransfer.files[0]); }}>
        <div className={`drop-zone ${isDragging ? "drop-zone-active" : ""}`}>
          <div className="upload-icon"><Upload size={18} /></div>
          <div className="drop-copy"><strong>{fileName}</strong><span>{transactions.length} transactions · PKR display · ready to review</span></div>
          <button className="button button-outline" onClick={() => fileInput.current?.click()}><FolderOpen size={15} /> Import statement</button>
          <input ref={fileInput} type="file" accept=".csv,text/csv" className="sr-only" onChange={(event) => handleFile(event.target.files?.[0])} />
        </div>
        <div className="pipeline"><div className="pipeline-step pipeline-done"><span>01</span><b>Import</b></div><div className="pipeline-line pipeline-line-done" /><div className="pipeline-step pipeline-current"><span>02</span><b>Sort with rules</b></div><div className="pipeline-line" /><div className="pipeline-step"><span>03</span><b>Review & export</b></div></div>
      </section>

      {issues.length > 0 && <div className="notice notice-warning"><CircleHelp size={17} /><div><strong>Needs a quick check</strong><span>{issues.join(" ")}</span></div><button className="icon-button" aria-label="Dismiss notices" onClick={() => setIssues([])}><X size={16} /></button></div>}

      <section className="stats-grid" aria-label="Statement summary">
        <StatCard label="Tracked spend" value={`PKR ${summary.spend.toLocaleString("en-US", { minimumFractionDigits: 2 })}`} note="excluding transfers" tone="teal" />
        <StatCard label="Rules matched" value={`${summary.auto}`} note={`${summary.coverage}% of statement covered`} tone="blue" />
        <StatCard label="Needs your eyes" value={`${summary.review}`} note={summary.review ? "review before export" : "nothing waiting"} tone="clay" />
        <StatCard label="Reviewed by you" value={`${summary.reviewed}`} note="manual decisions" tone="ink" />
      </section>

      <div className="content-grid">
        <section className="ledger-panel panel-card">
          <div className="panel-heading"><div><div className="eyebrow">Transaction ledger</div><h2>Every row, accounted for.</h2></div><div className="panel-heading-meta"><span className="mini-rule"><span className="mini-rule-dot" /> code-owned rules</span><span>{visibleRows.length} of {transactions.length}</span></div></div>
          <div className="toolbar"><div className="search-field"><Search size={16} /><input aria-label="Search transactions" placeholder="Search merchant or date" value={query} onChange={(event) => setQuery(event.target.value)} /></div><div className="filter-group"><Filter size={14} /><button className={activeFilter === "all" ? "filter-active" : ""} onClick={() => setActiveFilter("all")}>All</button><button className={activeFilter === "needs_review" ? "filter-active filter-review" : ""} onClick={() => setActiveFilter("needs_review")}>Needs review {summary.review > 0 && <span>{summary.review}</span>}</button><button className={activeFilter === "categorized" ? "filter-active" : ""} onClick={() => setActiveFilter("categorized")}>Auto</button></div></div>
          <div className="table-wrap"><table><thead><tr><th className="col-date">Date</th><th>Merchant / memo</th><th className="col-amount">Amount</th><th>Category</th><th className="col-status">Decision</th></tr></thead><tbody>{visibleRows.map((transaction) => <tr key={transaction.id} className={transaction.status === "needs_review" ? "row-review" : ""}>
            <td className="date-cell">{formatDate(transaction.date)}</td><td><div className="merchant-cell"><span className="merchant-name">{transaction.description || "Untitled transaction"}</span><span className="rule-cell">{transaction.ruleLabel}</span></div></td><td className={`amount-cell ${transaction.amount !== null && transaction.amount > 0 ? "amount-positive" : ""}`}>{formatMoney(transaction.amount)}</td><td><button className={`${categoryClass(transaction.category)} category-button`} onClick={() => setCategoryFilter(transaction.category)}>{transaction.category}<ChevronDown size={12} /></button></td><td><StatusPill transaction={transaction} /></td>
          </tr>)}</tbody></table>{visibleRows.length === 0 && <div className="empty-table"><Search size={22} /><strong>No transactions match</strong><span>Try another search or clear the filters.</span></div>}</div>
          <div className="table-footer"><span><ShieldCheck size={14} /> Every auto-result includes its matching rule.</span><button className="text-button" onClick={() => setActiveFilter("all")}>Show all rows <ArrowUpRight size={14} /></button></div>
        </section>

        <aside className="right-rail">
          <section className="review-card panel-card">
            <div className="review-card-top"><div><div className="eyebrow eyebrow-clay">Human in the loop</div><h2>Needs your eyes <span className="review-number">{reviewRows.length}</span></h2></div><CircleHelp className="review-header-icon" size={20} /></div>
            <p className="review-intro">A rule did not earn enough confidence. Choose a category and mark it reviewed.</p>
            {reviewRows.length > 0 ? <>
              <div className="review-batch"><label className="batch-check"><input type="checkbox" checked={reviewRows.length > 0 && selectedReviewIds.length === reviewRows.length} onChange={() => setSelectedReviewIds(selectedReviewIds.length === reviewRows.length ? [] : reviewRows.map((item) => item.id))} /><span>Select all</span></label><select value={batchCategory} onChange={(event) => setBatchCategory(event.target.value as Category)} aria-label="Batch category"><option value="Software">Software</option><option value="Travel">Travel</option><option value="Meals">Meals</option><option value="Office supplies">Office supplies</option><option value="Equipment">Equipment</option><option value="Advertising">Advertising</option><option value="Needs review">Needs review</option></select><button className="batch-apply" disabled={selectedReviewIds.length === 0} onClick={() => applyReview(selectedReviewIds, batchCategory)}>Apply</button></div>
              <div className="review-list">{reviewRows.map((transaction) => <div className="review-item" key={transaction.id}>
                <div className="review-item-check"><input type="checkbox" checked={selectedReviewIds.includes(transaction.id)} onChange={() => selectReview(transaction.id)} /></div><div className="review-item-content"><div className="review-item-heading"><div><strong>{transaction.description || "Untitled transaction"}</strong><span>{formatDate(transaction.date)} · {formatMoney(transaction.amount)}</span></div><span className="review-flag">question</span></div><p>{transaction.reviewReason ?? transaction.ruleLabel}</p><div className="review-item-actions"><select value={draftCategories[transaction.id] ?? "Needs review"} onChange={(event) => updateDraft(transaction.id, event.target.value as Category)} aria-label={`Category for ${transaction.description}`}><option value="Needs review">Needs review</option>{spendingCategories.map((category) => <option key={category} value={category}>{category}</option>)}<option value="Refund">Refund</option><option value="Income">Income</option><option value="Transfer / non-spend">Transfer / non-spend</option></select><button onClick={() => applyReview([transaction.id])}>Mark reviewed <Check size={13} /></button></div></div>
              </div>)}</div>
            </> : <div className="review-empty"><div className="review-empty-icon"><Check size={20} /></div><strong>Clean slate.</strong><span>Every row has a rule or a decision.</span></div>}
          </section>

          <section className="breakdown-card panel-card"><div className="panel-heading compact"><div><div className="eyebrow">Business spend</div><h2>Where it went</h2></div><button className="icon-button" aria-label="Refresh breakdown" onClick={() => setTransactions([...transactions])}><RefreshCw size={15} /></button></div><div className="breakdown-list">{categoryTotals.map(({ category, total }) => <button key={category} className="breakdown-row" onClick={() => { setCategoryFilter(category); setActiveFilter("all"); }}><span className={`breakdown-dot dot-${categoryColors[category] ?? "stone"}`} /><span>{category}</span><strong>PKR {total.toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong></button>)}</div><div className="breakdown-foot"><span>Sorted by total</span>{categoryFilter && <button onClick={() => setCategoryFilter(null)}>Clear filter <X size={12} /></button>}</div></section>
        </aside>
      </div>
      <footer className="workspace-footer"><span>simplke · a transparent second pair of eyes</span><span><Sparkles size={13} /> Categorization is deterministic code, not a model prediction.</span></footer>
    </main>
  </div>;
}
