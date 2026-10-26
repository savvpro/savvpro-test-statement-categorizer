import { useEffect, useMemo, useState } from "react";
import { Upload, FileSpreadsheet, CheckCircle2, AlertCircle, RefreshCw, Download, Wallet, ArrowUpRight, Search } from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
// Fallback list; the real list is loaded from the backend (/api/categories).
const DEFAULT_CATEGORIES = [
  "Software", "Travel", "Office Supplies", "Advertising",
  "Phone & Internet", "Bank Fees", "Education & Training", "Groceries", "Meals",
  "Income", "Transfer", "Needs Review"
];

// Stop spreadsheet apps from running cells that start with = + - @ as formulas.
function safeCell(value) {
  const text = String(value ?? "");
  return /^[=+\-@\t\r]/.test(text) ? `'${text}` : text;
}

function money(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD"
  }).format(value || 0);
}

export default function App() {
  const [transactions, setTransactions] = useState([]);
  const [fileName, setFileName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("All");
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES);

  useEffect(() => {
    fetch(`${API}/api/categories`)
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(d => Array.isArray(d.categories) && setCategories(d.categories))
      .catch(() => {});
  }, []);

  async function uploadFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a CSV file.");
      return;
    }

    setLoading(true);
    setError("");
    const form = new FormData();
    form.append("file", file);

    try {
      const response = await fetch(`${API}/api/categorize`, {
        method: "POST", body: form
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not process this file.");
      setTransactions(data.transactions);
      setFileName(file.name);
    } catch (err) {
      setError(`${err.message}. Make sure the Python backend is running.`);
    } finally {
      setLoading(false);
    }
  }

  async function loadSample() {
    try {
      const response = await fetch("/sample_statement.csv");
      if (!response.ok) throw new Error("Sample file could not be loaded.");
      const file = await response.blob();
      await uploadFile(new File([file], "sample_statement.csv", { type: "text/csv" }));
    } catch (err) {
      setError("Could not load sample. Use the provided sample_data/sample_statement.csv file instead.");
    }
  }

  function changeCategory(id, category) {
    setTransactions(previous => previous.map(tx => {
      if (tx.id !== id) return tx;
      return {
        ...tx,
        category,
        kind: category === "Needs Review" ? "review"
          : category === "Transfer" ? "transfer"
          : category === "Income" ? "income"
          : tx.amount < 0 || tx.kind === "refund" ? "refund" : "expense",
        manually_reviewed: true
      };
    }));
  }

  const filtered = useMemo(() => transactions.filter(tx => {
    const matchesSearch = tx.description.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === "All" ||
      (filter === "Needs Review" && tx.category === "Needs Review") ||
      (filter === "Transfers" && tx.kind === "transfer") ||
      (filter === "Income" && tx.kind === "income") ||
      (filter === "Expenses" && ["expense", "refund"].includes(tx.kind));
    return matchesSearch && matchesFilter;
  }), [transactions, search, filter]);

  const totals = useMemo(() => {
    let expenses = 0, income = 0, transfers = 0, review = 0, reviewAmount = 0;
    const categories = {};
    transactions.forEach(tx => {
      if (tx.kind === "transfer") transfers += Math.abs(tx.amount);
      else if (tx.kind === "income") income += Math.abs(tx.amount);
      else if (tx.category === "Needs Review") { review++; reviewAmount += Math.abs(tx.amount); }
      else if (tx.kind === "expense" || tx.kind === "refund") {
        const signed = tx.kind === "refund" ? -Math.abs(tx.amount) : Math.abs(tx.amount);
        expenses += signed;
        categories[tx.category] = (categories[tx.category] || 0) + signed;
      }
    });
    return { expenses, income, transfers, review, reviewAmount, categories };
  }, [transactions]);

  function exportCsv() {
    const columns = ["date", "description", "amount", "category", "kind", "reason", "manually_reviewed"];
    const rows = [
      columns.join(","),
      ...transactions.map(tx => columns.map(key =>
        `"${safeCell(tx[key]).replaceAll('"', '""')}"`
      ).join(","))
    ];
    const url = URL.createObjectURL(new Blob([rows.join("\n")], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "categorized_statement.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  const reviewed = transactions.filter(tx => tx.manually_reviewed).length;
  const unresolved = transactions.filter(tx => tx.category === "Needs Review").length;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-icon"><Wallet size={21}/></span><span>ClearLedger</span></div>
        <div className="side-label">WORKSPACE</div>
        <div className="side-link active"><FileSpreadsheet size={18}/> Statement review</div>
        <div className="side-note">Freelancer edition</div>
        <div className="sidebar-bottom">
          <div className="avatar">CL</div>
          <div><strong>Local workspace</strong><small>Your data stays in this session</small></div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar"><span>Workspace / Statements</span><span className="secure"><CheckCircle2 size={15}/> Rule-based categorization</span></header>
        <section className="page-heading">
          <div><div className="eyebrow">FINANCE WORKSPACE</div><h1>Statement categorizer</h1><p>Organize business transactions, review uncertain items, and prepare your records.</p></div>
          <button className="btn secondary" onClick={exportCsv} disabled={!transactions.length}><Download size={16}/> Export CSV</button>
        </section>

        <section className="upload-panel">
          <div className="upload-icon"><Upload size={23}/></div>
          <div className="upload-copy"><h3>Upload a bank statement</h3><p>CSV files with date (optional), description, and amount columns. Maximum 5 MB.</p></div>
          <label className="btn primary">{loading ? "Processing..." : "Choose CSV"}<input type="file" accept=".csv,text/csv" disabled={loading} onChange={e => uploadFile(e.target.files?.[0])}/></label>
          <button className="btn secondary" onClick={loadSample} disabled={loading}>Try sample</button>
        </section>
        {fileName && <div className="file-banner"><FileSpreadsheet size={17}/><span><strong>{fileName}</strong> processed successfully</span><button onClick={() => {setTransactions([]);setFileName("");}}>Clear</button></div>}
        {error && <div className="error-banner"><AlertCircle size={17}/>{error}</div>}

        <section className="stats-grid">
          <div className="stat-card"><div className="stat-top"><span>Net expenses</span><Wallet size={17}/></div><strong>{money(totals.expenses)}</strong><small>Refunds reduce expenses</small></div>
          <div className="stat-card"><div className="stat-top"><span>Business income</span><ArrowUpRight size={17}/></div><strong>{money(totals.income)}</strong><small>Matched income rules</small></div>
          <div className="stat-card"><div className="stat-top"><span>Needs review</span><AlertCircle size={17}/></div><strong>{totals.review}</strong><small>{money(totals.reviewAmount)} not yet categorized</small></div>
          <div className="stat-card"><div className="stat-top"><span>Manually reviewed</span><CheckCircle2 size={17}/></div><strong>{reviewed}</strong><small>{transactions.length} transactions total</small></div>
        </section>

        <section className="content-card">
          <div className="table-heading"><div><h2>Transactions</h2><p>Review and correct the suggested category for each row.</p></div><span className="count-pill">{filtered.length} rows</span></div>
          <div className="toolbar"><div className="search-box"><Search size={17}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search transactions..."/></div><select value={filter} onChange={e => setFilter(e.target.value)}><option>All</option><option>Needs Review</option><option>Expenses</option><option>Income</option><option>Transfers</option></select></div>
          <div className="table-wrap"><table><thead><tr><th>DATE</th><th>DESCRIPTION</th><th>AMOUNT</th><th>CATEGORY</th><th>STATUS</th></tr></thead>
            <tbody>{filtered.map(tx => <tr key={tx.id}>
              <td className="date-cell">{tx.date || "—"}</td>
              <td><div className="description">{tx.description || "Missing description"}</div><div className="reason">{tx.reason}</div></td>
              <td className="amount">{money(tx.amount)}</td>
              <td><select className={`category-select ${tx.category === "Needs Review" ? "needs-review" : ""}`} value={tx.category} onChange={e => changeCategory(tx.id, e.target.value)}>{categories.map(c => <option key={c}>{c}</option>)}</select></td>
              <td>{tx.category === "Needs Review" ? <span className="status review"><AlertCircle size={13}/> Review</span> : tx.manually_reviewed ? <span className="status edited"><CheckCircle2 size={13}/> Edited</span> : <span className="status matched"><CheckCircle2 size={13}/> Matched</span>}</td>
            </tr>)}
            {!filtered.length && <tr><td colSpan="5" className="empty"><FileSpreadsheet size={28}/><strong>No transactions to show</strong><span>Upload a CSV or change your filters.</span></td></tr>}
          </tbody></table></div>
          {transactions.length > 0 && <div className="table-footer"><span><RefreshCw size={14}/> {unresolved} transaction(s) still need attention</span><span>Edits apply to this browser session</span></div>}
        </section>

        <section className="bottom-grid"><div className="content-card category-card"><h2>Expense breakdown</h2><p>Net totals by matched category, with refunds subtracted.</p>
          {Object.entries(totals.categories).length ? Object.entries(totals.categories).sort((a,b) => b[1]-a[1]).map(([name,value]) => <div className="breakdown-row" key={name}><span>{name}</span><strong>{money(value)}</strong></div>) : <div className="subtle-empty">Your category totals will appear here after upload.</div>}
        </div><div className="content-card note-card"><div className="note-icon"><AlertCircle size={19}/></div><h2>Keep your records accurate</h2><p>Transfers ({money(totals.transfers)} in this file) are excluded from expenses. Known refunds reduce the matching expense category. Unknown merchants remain in Needs Review until you check them.</p><small>Rules are deterministic and can be updated in backend/categorizer.py.</small></div></section>
        <footer>ClearLedger · Demo with synthetic data · No bank credentials required</footer>
      </main>
    </div>
  );
}

