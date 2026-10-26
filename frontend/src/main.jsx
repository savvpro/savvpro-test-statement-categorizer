import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const CATEGORIES = ["Software", "Travel", "Meals", "Office supplies", "Professional services", "Advertising", "Income", "Transfer", "Refund", "Needs review"];
const demoCsv = `Date,Description,Amount
2026-01-02,ADOBE CREATIVE CLOUD,-59.99
2026-01-03,UBER *TRIP,-24.60
2026-01-04,TRANSFER TO SAVINGS,-500.00
2026-01-06,JOES CAFE 9921,-18.25
2026-01-09,CLIENT PAYMENT ACME,2400.00`;

const money = (amount) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(amount);
const api = async (path, options = {}) => {
  const token = localStorage.getItem("studio_token");
  const response = await fetch(`${API_URL}${path}${path.includes("?") ? "&" : "?"}token=${encodeURIComponent(token || "")}`, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "Something went wrong.");
  return body;
};
const navigate = (path) => { window.history.pushState({}, "", path); window.dispatchEvent(new PopStateEvent("popstate")); };

function Login({ onLogin }) {
  const [email, setEmail] = useState("demo@studioledger.com");
  const [password, setPassword] = useState("demo123");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  async function submit(event) {
    event.preventDefault(); setLoading(true); setError("");
    try { const result = await api("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) }); localStorage.setItem("studio_token", result.token); onLogin(result.user); navigate("/app"); }
    catch (requestError) { setError(requestError.message); } finally { setLoading(false); }
  }
  return <main className="auth-page"><div className="auth-brand"><span className="brand-mark">SL</span><strong>Studio Ledger</strong></div><div className="auth-card"><div className="auth-icon">SL</div><p className="eyebrow">WELCOME BACK</p><h1>Your books, in order.</h1><p className="auth-copy">Sign in to your private workspace and pick up where you left off.</p><form onSubmit={submit}><label>Email<input value={email} onChange={(event) => setEmail(event.target.value)} type="email" /></label><label>Password<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" /></label>{error && <div className="error">{error}</div>}<button className="button primary" disabled={loading}>{loading ? "Signing in..." : "Sign in to workspace"}</button></form><div className="demo-credentials"><strong>Demo workspace</strong><span>demo@studioledger.com</span><span>demo123</span></div></div><p className="auth-footer">Private by design · Deterministic categorization</p></main>;
}

function Shell({ user, children, page }) {
  const links = [["/app", "Overview", "⌂"], ["/app/transactions", "Transactions", "↔"], ["/app/rules", "Rules & logic", "◇"], ["/app/settings", "Settings", "⚙"]];
  function signOut() { localStorage.removeItem("studio_token"); navigate("/login"); }
  return <div className="app-shell"><aside className="sidebar"><div className="side-brand"><span className="brand-mark">SL</span><strong>Studio Ledger</strong></div><div className="workspace-switch"><span className="workspace-avatar">AM</span><span><b>{user.workspace}</b><small>Personal workspace</small></span><span>⌄</span></div><nav>{links.map(([href, label, icon]) => <a className={page === href ? "active" : ""} href={href} onClick={(event) => { event.preventDefault(); navigate(href); }} key={href}><span>{icon}</span>{label}{label === "Transactions" && <em>1</em>}</a>)}</nav><div className="side-bottom"><div className="privacy-note"><span>✓</span><div><b>Your data stays local</b><small>No third-party AI decisions</small></div></div><button className="profile" onClick={signOut}><span className="profile-avatar">AM</span><span><b>{user.name}</b><small>Sign out</small></span><span>⋮</span></button></div></aside><div className="app-main"><header className="app-header"><div><span className="mobile-brand">SL</span><span className="breadcrumb">Morgan Design Co. <b>/</b> {page === "/app" ? "Overview" : page.split("/").pop().replace("-", " ")}</span></div><div className="header-actions"><span className="status-dot">●</span> Demo data <button className="bell">♧</button></div></header>{children}</div></div>;
}

function Overview({ data, onUpload }) {
  const transactions = data.transactions; const reviewCount = transactions.filter((item) => item.category === "Needs review").length; const categorized = Math.round(((transactions.length - reviewCount) / transactions.length) * 100);
  return <div className="page"><div className="page-heading"><div><p className="eyebrow">MONDAY, JANUARY 12, 2026</p><h1>Good morning, Alex <span>✦</span></h1><p className="muted">Here's the latest from your studio finances.</p></div><button className="button primary compact" onClick={() => document.getElementById("statement-input").click()}>↑ Upload statement</button><input id="statement-input" type="file" accept=".csv" hidden onChange={(event) => event.target.files[0] && onUpload(event.target.files[0])} /></div><div className="stat-grid"><div className="stat-card featured"><span>Total activity</span><strong>{money(transactions.reduce((sum, item) => sum + item.amount, 0))}</strong><small>January 2026 <i>↗ 12.4%</i></small><div className="mini-chart"><i /><i /><i /><i /><i /><i /><i /></div></div><div className="stat-card"><span>Business spending</span><strong>{money(Math.abs(transactions.filter((item) => item.amount < 0 && !["Transfer", "Needs review"].includes(item.category)).reduce((sum, item) => sum + item.amount, 0)))}</strong><small>4 transactions</small></div><div className="stat-card"><span>Client income</span><strong className="green">{money(transactions.filter((item) => item.category === "Income").reduce((sum, item) => sum + item.amount, 0))}</strong><small>1 payment received</small></div><div className="stat-card"><span>Needs review</span><strong className="amber">{reviewCount}</strong><small>{reviewCount ? "Action needed" : "You're all caught up"}</small></div></div><div className="content-grid"><section className="panel recent-panel"><div className="panel-heading"><div><h2>Recent transactions</h2><p>From your latest statement</p></div><a href="/app/transactions" onClick={(event) => { event.preventDefault(); navigate("/app/transactions"); }}>View all →</a></div><TransactionRows transactions={transactions.slice(0, 4)} compact /></section><section className="panel progress-panel"><div className="panel-heading"><div><h2>Statement health</h2><p>January statement</p></div><span className="health-score">{categorized}%</span></div><div className="progress-ring" style={{ "--progress": `${categorized * 3.6}deg` }}><div><strong>{categorized}%</strong><small>categorized</small></div></div>{reviewCount ? <button className="review-link" onClick={() => navigate("/app/transactions?filter=Needs%20review")}>Review {reviewCount} transaction →</button> : <p className="all-good">✓ Everything looks good</p>}<div className="legend"><span><i className="green-dot" />Auto-categorized</span><span><i className="orange-dot" />Needs review</span></div></section></div><section className="principle"><span className="principle-icon">✦</span><div><p className="eyebrow">THE STUDIO LEDGER PRINCIPLE</p><h2>A careful answer beats a confident guess.</h2><p>Our rules explain every match. When the signal isn't strong enough, we stop and ask you instead.</p></div><a href="/app/rules" onClick={(event) => { event.preventDefault(); navigate("/app/rules"); }}>See how it works →</a></section></div>;
}

function TransactionRows({ transactions, compact = false, onUpdate }) {
  return <div className="transaction-list">{transactions.map((item) => <div className="transaction-row" key={item.id}><div className={`merchant-icon ${item.category.toLowerCase().replaceAll(" ", "-")}`}>{item.category === "Software" ? "✦" : item.category === "Travel" ? "↗" : item.category === "Income" ? "↓" : "?"}</div><div className="transaction-main"><b>{item.description}</b><small>{item.date} · {item.reason}</small></div><strong className={item.amount > 0 ? "amount-positive" : ""}>{money(item.amount)}</strong>{!compact && <select value={item.category} onChange={(event) => onUpdate(item.id, event.target.value)}>{CATEGORIES.map((category) => <option key={category}>{category}</option>)}</select>}<span className={`category-tag ${item.category === "Needs review" ? "tag-review" : ""}`}>{item.category}</span></div>)}</div>;
}

function Transactions({ data, setData }) {
  const [filter, setFilter] = useState(new URLSearchParams(window.location.search).get("filter") || "All");
  const visible = useMemo(() => data.transactions.filter((item) => filter === "All" || item.category === filter), [data, filter]);
  function update(id, category) { setData((current) => ({ ...current, transactions: current.transactions.map((item) => item.id === id ? { ...item, category, confidence: "manual", reason: "Updated by you during review." } : item) })); }
  function exportCsv() { const rows = ["Date,Description,Amount,Category", ...data.transactions.map((item) => `${item.date},"${item.description}",${item.amount},${item.category}`)]; const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob([rows.join("\n")], { type: "text/csv" })); link.download = "studio-ledger-categorized.csv"; link.click(); }
  return <div className="page"><div className="page-heading"><div><p className="eyebrow">JANUARY 2026 · STATEMENT</p><h1>Transactions</h1><p className="muted">Review, correct, and export your categorized activity.</p></div><button className="button outline compact" onClick={exportCsv}>↓ Export CSV</button></div><div className="filter-bar"><div>{["All", ...CATEGORIES].map((category) => <button className={filter === category ? "selected" : ""} onClick={() => setFilter(category)} key={category}>{category}</button>)}</div><span>{visible.length} of {data.transactions.length} transactions</span></div><section className="panel transactions-panel"><div className="table-head"><span>TRANSACTION</span><span>AMOUNT</span><span>CATEGORY</span></div><TransactionRows transactions={visible} onUpdate={update} /></section></div>;
}

function Rules() { const [rules, setRules] = useState(null); useEffect(() => { api("/api/rules").then((result) => setRules(result.rules)); }, []); return <div className="page"><div className="page-heading"><div><p className="eyebrow">TRANSPARENT BY DEFAULT</p><h1>Rules & logic</h1><p className="muted">The exact signals Studio Ledger uses to categorize your work.</p></div></div><section className="rules-intro"><span className="principle-icon">◇</span><div><h2>No black box. Ever.</h2><p>Studio Ledger uses a deliberate, ordered ruleset. We check money movement first, then trusted merchants. If nothing matches, the transaction goes to Needs review.</p></div></section><div className="rules-grid">{(rules || []).map((rule, index) => <div className="rule-card" key={rule.category}><span className="rule-number">0{index + 1}</span><div><h3>{rule.category}</h3><p>{rule.description}</p><div className="keyword-list">{rule.keywords.map((keyword) => <span key={keyword}>{keyword}</span>)}</div></div></div>)}</div></div>; }

function Settings({ user }) { return <div className="page"><div className="page-heading"><div><p className="eyebrow">WORKSPACE</p><h1>Settings</h1><p className="muted">Manage your profile and workspace preferences.</p></div></div><section className="panel settings-panel"><h2>Profile</h2><p className="panel-subtitle">Your demo account details</p><label>Full name<input value={user.name} readOnly /></label><label>Email address<input value={user.email} readOnly /></label><label>Workspace name<input value={user.workspace} readOnly /></label><div className="settings-note">This is a demo workspace with seeded data from the Studio Ledger API.</div></section></div>; }

function App() {
  const [user, setUser] = useState(null); const [route, setRoute] = useState(window.location.pathname); const [data, setData] = useState(null); const [error, setError] = useState("");
  useEffect(() => { const onPop = () => setRoute(window.location.pathname); window.addEventListener("popstate", onPop); if (localStorage.getItem("studio_token")) api("/api/me").then(setUser).catch(() => localStorage.removeItem("studio_token")); return () => window.removeEventListener("popstate", onPop); }, []);
  useEffect(() => { if (user && !data) api("/api/dashboard").then(setData).catch((requestError) => setError(requestError.message)); }, [user, data]);
  async function uploadStatement(file) {
    const formData = new FormData();
    formData.append("file", file);
    try { setData(await api("/api/statements", { method: "POST", body: formData })); }
    catch (requestError) { setError(requestError.message); }
  }
  if (!user || route === "/login") return <Login onLogin={setUser} />;
  const page = route.startsWith("/app/transactions") ? "/app/transactions" : route.startsWith("/app/rules") ? "/app/rules" : route.startsWith("/app/settings") ? "/app/settings" : "/app";
  const content = error ? <div className="page"><div className="error">{error}</div></div> : !data ? <div className="loading-screen"><span className="spinner" /> Loading workspace...</div> : page === "/app" ? <Overview data={data} onUpload={uploadStatement} /> : page === "/app/transactions" ? <Transactions data={data} setData={setData} /> : page === "/app/rules" ? <Rules /> : <Settings user={user} />;
  return <Shell user={user} page={page}>{content}</Shell>;
}

createRoot(document.getElementById("root")).render(<App />);
