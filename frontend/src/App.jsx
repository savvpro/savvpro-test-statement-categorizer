import { useEffect, useState } from "react";
import { getCategories, updateCategory, uploadStatement } from "./api/client";
import UploadForm from "./components/UploadForm";
import TransactionTable from "./components/TransactionTable";
import CategorySummary from "./components/CategorySummary";
import "./styles/app.css";

const NAV = ["Categorizer", "Needs Review", "Tax Totals"];

function Logo() {
  return (
    <div className="logo">
      <svg width="30" height="30" viewBox="0 0 30 30" aria-hidden="true">
        <rect x="3" y="15" width="6" height="12" rx="2" fill="#0d9488" />
        <rect x="12" y="9" width="6" height="18" rx="2" fill="#14b8a6" />
        <rect x="21" y="3" width="6" height="24" rx="2" fill="#0b1b3a" />
      </svg>
      <span>FinLedger</span>
      <small className="logo-tag">Statement Categorizer</small>
    </div>
  );
}

export default function App() {
  const [categories, setCategories] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [summary, setSummary] = useState(null);
  const [skipped, setSkipped] = useState([]);
  const [loading, setLoading] = useState(false);
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getCategories().then(setCategories).catch((e) => setError(e.message));
  }, []);

  async function handleUpload(file) {
    setError("");
    setLoading(true);
    try {
      const data = await uploadStatement(file);
      setTransactions(data.transactions);
      setSummary(data.summary);
      setSkipped(data.skipped);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleChange(id, category) {
    setError("");
    setSavingId(id);
    try {
      const data = await updateCategory(id, category);
      setTransactions((prev) => prev.map((t) => (t.id === id ? data.transaction : t)));
      setSummary(data.summary);
    } catch (e) {
      setError(e.message);
    } finally {
      setSavingId(null);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="topbar-inner">
          <Logo />
          <nav className="nav" aria-label="Main">
            {NAV.map((item, i) => (
              <span key={item} className={i === 0 ? "nav-item active" : "nav-item"}>
                {item}
              </span>
            ))}
          </nav>
          <div className="account">
            <span className="avatar-sm">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="8" r="4" />
                <path d="M4 21c0-4 3.6-7 8-7s8 3 8 7" />
              </svg>
            </span>
            <span className="account-label">My Account</span>
          </div>
        </div>
      </header>

      <main className="container">
        <section className="hero">
          <span className="eyebrow">Tax-time helper for freelance designers</span>
          <h1>
            Sort every transaction.
            <br />
            Be ready for tax time.
          </h1>
          <p>
            Upload your business bank or credit card statement. Our rule-based engine
            categorizes each transaction, flags anything it isn&apos;t sure about as
            Needs Review, and gives you totals per category. Use fake data only.
          </p>
        </section>

        {error && (
          <div className="error" role="alert">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4M12 16h.01" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <UploadForm onUpload={handleUpload} loading={loading} />

        {summary && (
          <>
            <TransactionTable
              transactions={transactions}
              categories={categories}
              onChange={handleChange}
              savingId={savingId}
            />
            <CategorySummary summary={summary} skipped={skipped} />
          </>
        )}
      </main>
    </div>
  );
}
