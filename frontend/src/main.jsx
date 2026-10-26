import { StrictMode, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const CATEGORIES = ["Client Income", "Software", "Advertising & Marketing", "Internet & Phone", "Equipment", "Payment Processing Fees", "Travel & Transport", "Travel", "Meals", "Food & Dining", "Transport", "Shopping", "Utilities", "Health", "Entertainment", "Education", "Personal Care", "Electronics", "Office Expenses", "Taxes", "Transfer", "Refund", "Personal Expense", "Other", "Needs Review"];

function App() {
  const [token, setToken] = useState(localStorage.getItem("session"));
  const [username, setUsername] = useState("");
  const [login, setLogin] = useState({ username: "demo", password: "demo-password-change-me" });
  const [workspaceId, setWorkspaceId] = useState("freelancer-demo");
  const [workspaceName, setWorkspaceName] = useState("Freelancer Demo");
  const [statement, setStatement] = useState(null);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [filter, setFilter] = useState("All");
  const [history, setHistory] = useState([]);
  const [audit, setAudit] = useState([]);
  const headers = () => ({ Authorization: `Bearer ${token}`, "X-Workspace-Id": workspaceId });

  async function signIn(event) {
    event.preventDefault(); setError("");
    const response = await fetch(`${API}/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(login) });
    const body = await response.json();
    if (!response.ok) return setError(body.detail || "Could not sign in.");
    localStorage.setItem("session", body.token); setToken(body.token); setUsername(body.username);
  }

  async function loadWorkspace(nextWorkspaceId = workspaceId) {
    const requestHeaders = { Authorization: `Bearer ${token}`, "X-Workspace-Id": nextWorkspaceId };
    const [historyResponse, auditResponse] = await Promise.all([
      fetch(`${API}/statements`, { headers: requestHeaders }),
      fetch(`${API}/audit`, { headers: requestHeaders }),
    ]);
    if (historyResponse.ok) setHistory(await historyResponse.json());
    if (auditResponse.ok) setAudit(await auditResponse.json());
  }

  async function upload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true); setError("");
    const form = new FormData(); form.append("file", file);
    try {
      const response = await fetch(`${API}/statements`, { method: "POST", headers: headers(), body: form });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Upload failed.");
      setStatement(body);
      loadWorkspace();
    } catch (reason) { setError(reason.message); }
    finally { setUploading(false); }
  }

  async function correct(transactionId, category) {
    const response = await fetch(`${API}/statements/${statement.id}/transactions/${transactionId}`, {
      method: "PATCH", headers: { ...headers(), "Content-Type": "application/json" },
      body: JSON.stringify({ category, learn: true }),
    });
    const updated = await response.json();
    if (!response.ok) { setError(updated.detail || "Could not save correction."); return; }
    setStatement((current) => ({ ...current, transactions: current.transactions.map((item) => item.id === updated.id ? updated : item) }));
    loadWorkspace();
  }

  const transactions = statement?.transactions ?? [];
  const summary = useMemo(() => transactions.reduce((result, item) => {
    result[item.category] = (result[item.category] || 0) + Number(item.amount); return result;
  }, {}), [transactions]);
  const visible = transactions.filter((item) => filter === "All" || (filter === "Needs review" ? item.needs_review : item.category === filter));

  if (!token) return <main><section className="login-card"><span className="mark">F</span><p className="eyebrow">WELCOME BACK</p><h1>Better books, less guesswork.</h1><p>Sign in to your private workspace and review your transactions.</p><form onSubmit={signIn}><input placeholder="Username" value={login.username} onChange={(e) => setLogin({ ...login, username: e.target.value })}/><input type="password" placeholder="Password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })}/><button className="upload">Sign in</button></form>{error && <div className="error">{error}</div>}<small>Local demo: demo / demo-password-change-me</small></section></main>;
  return <main>
    <header><div className="brand"><span className="mark">F</span><div><strong>FreelanceBooks</strong><small>Clear books for independent work</small></div></div><div className="workspace"><span>{username || "Workspace"}</span><select value={workspaceId} onChange={(event) => { const next = event.target.value; setWorkspaceId(next); setWorkspaceName(event.target.options[event.target.selectedIndex].text); setStatement(null); loadWorkspace(next); }}><option value="freelancer-demo">Freelancer Demo</option><option value="agency-demo">Small Agency Demo</option></select><b>{workspaceName}</b><button onClick={() => { localStorage.removeItem("session"); setToken(null); }}>Sign out</button></div></header>
    <section className="hero"><p className="eyebrow">STATEMENT REVIEW</p><h1>Know where your money went.</h1><p>Upload a CSV and get an explainable first pass on your freelance finances. You stay in control of every decision.</p><label className="upload">{uploading ? "Reading statement..." : "Upload CSV statement"}<input type="file" accept=".csv" onChange={upload} disabled={uploading} /></label>{error && <div className="error">{error}</div>}<p className="hint">Use the sample format: Date, Description, Amount, Currency, Type</p></section>
    {statement && <><section className="metrics"><Metric label="Transactions" value={transactions.length}/><Metric label="Needs review" value={transactions.filter((item) => item.needs_review).length} accent/><Metric label="Income" value={money(summary["Client Income"] || 0)} /><Metric label="Expenses" value={money(Object.entries(summary).filter(([key]) => !["Client Income", "Transfer", "Refund"].includes(key)).reduce((sum, [, value]) => sum + value, 0))}/></section>
      <section className="panel"><div className="panel-heading"><div><p className="eyebrow">YOUR STATEMENT</p><h2>{statement.filename}</h2></div><div className="legend"><span className="dot high"/>Confident <span className="dot review"/>Review recommended</div></div>
        <div className="filters"><button className={filter === "All" ? "active" : ""} onClick={() => setFilter("All")}>All ({transactions.length})</button><button className={filter === "Needs review" ? "active" : ""} onClick={() => setFilter("Needs review")}>Needs review ({transactions.filter((item) => item.needs_review).length})</button>{["Client Income", "Software", "Travel & Transport", "Meals"].map((item) => <button className={filter === item ? "active" : ""} key={item} onClick={() => setFilter(item)}>{item}</button>)}</div>
        <div className="table-wrap"><table><thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Category</th><th>Confidence</th><th>Why</th></tr></thead><tbody>{visible.map((item) => <tr key={item.id}><td>{item.date || "—"}</td><td><strong>{item.description}</strong><small>{item.direction}</small></td><td className={item.direction === "income" ? "income" : ""}>{item.direction === "income" ? "+" : "-"}{money(item.amount)} {item.currency}</td><td><select value={item.category} onChange={(event) => correct(item.id, event.target.value)}>{CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select></td><td><span className={`confidence ${item.needs_review ? "needs-review" : ""}`}>{item.confidence ? `${item.confidence}%` : "—"}</span></td><td className="explanation">{item.explanation}{item.rule_scope === "user" && <em>Personal rule</em>}{item.rule_scope === "shared" && <em>Shared default</em>}</td></tr>)}</tbody></table></div>
      </section><section className="learning"><div><span className="spark">✦</span><div><h3>Your corrections make this smarter</h3><p>When you change a category, FreelanceBooks saves a private rule for your workspace. It will recognize the same merchant next time.</p></div></div><span className="shield">Shared defaults never override your rules</span></section></>}
    {!statement && <section className="empty"><h2>Start with a statement</h2><p>Your first review will include confidence scores, explanations, and a safe correction loop.</p></section>}
    <section className="activity-grid"><div className="activity-card"><p className="eyebrow">STATEMENT HISTORY</p><h2>{history.length} saved statements</h2>{history.slice(0, 5).map((item) => <div className="activity-row" key={item.id}><span>{item.filename}</span><small>{item.transaction_count} transactions · {item.review_count} to review</small></div>)}{history.length === 0 && <p className="muted">Upload a statement to create history.</p>}</div><div className="activity-card"><p className="eyebrow">AUDIT TRAIL</p><h2>{audit.length} corrections recorded</h2>{audit.slice(0, 5).map((item) => <div className="activity-row" key={item.id}><span>{item.old_category} → {item.new_category}</span><small>{item.created_at}</small></div>)}{audit.length === 0 && <p className="muted">Your category corrections will appear here.</p>}</div></section>
  </main>;
}

function Metric({ label, value, accent }) { return <div className={`metric ${accent ? "accent" : ""}`}><span>{label}</span><strong>{value}</strong></div>; }
function money(value) { return `$${Number(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }
createRoot(document.getElementById("root")).render(<StrictMode><App /></StrictMode>);
