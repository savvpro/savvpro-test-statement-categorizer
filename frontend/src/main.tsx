import { StrictMode } from "react";
import { ChangeEvent, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Transaction = {
  source_row: number;
  date: string;
  description: string;
  amount: string;
  category: string;
  confidence: string;
  reason: string;
  needs_review: boolean;
};

type Summary = {
  spending_total: string;
  refund_total: string;
  transfer_total: string;
  review_total: string;
  transaction_count: number;
  review_count: number;
  category_totals: Record<string, string>;
};

const CATEGORIES = [
  "Software",
  "Office Supplies",
  "Travel",
  "Meals",
  "Advertising",
  "Professional Services",
  "Banking Fees",
  "Refund",
  "Transfer",
  "Personal",
  "Needs Review",
];

function buildSummary(items: Transaction[]): Summary {
  const totals: Record<string, number> = {};
  let spending = 0;
  let refunds = 0;
  let transfers = 0;
  let review = 0;
  items.forEach((item) => {
    const amount = Number(item.amount);
    totals[item.category] = (totals[item.category] ?? 0) + amount;
    if (item.category === "Refund") refunds += amount;
    else if (item.category === "Transfer") transfers += amount;
    else spending += amount;
    if (item.needs_review) review += amount;
  });
  return {
    spending_total: spending.toFixed(2),
    refund_total: refunds.toFixed(2),
    transfer_total: transfers.toFixed(2),
    review_total: review.toFixed(2),
    transaction_count: items.length,
    review_count: items.filter((item) => item.needs_review).length,
    category_totals: Object.fromEntries(Object.entries(totals).map(([key, value]) => [key, value.toFixed(2)])),
  };
}

function App() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [showReviewOnly, setShowReviewOnly] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    setError("");
    setIsLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch("http://localhost:8000/statements/categorize", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Unable to read this statement.");
      setTransactions(payload.transactions);
      setSummary(payload.summary);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to read this statement.");
      setTransactions([]);
      setSummary(null);
    } finally {
      setIsLoading(false);
    }
  }

  function updateCategory(sourceRow: number, category: string) {
    const updated = transactions.map((transaction) =>
      transaction.source_row === sourceRow
        ? {
            ...transaction,
            category,
            confidence: "user",
            reason: "Category selected by the user.",
            needs_review: false,
          }
        : transaction,
    );
    setTransactions(updated);
    setSummary(buildSummary(updated));
  }

  function exportTransactions() {
    const fields = ["source_row", "date", "description", "amount", "category", "confidence", "reason", "needs_review"];
    const escapeCsv = (value: string | number | boolean) => `"${String(value).replaceAll('"', '""')}"`;
    const csv = [
      fields.join(","),
      ...transactions.map((transaction) => fields.map((field) => escapeCsv(transaction[field as keyof Transaction])).join(",")),
    ].join("\n");
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    link.download = "categorized-statement.csv";
    link.click();
    URL.revokeObjectURL(link.href);
  }

  const visibleTransactions = showReviewOnly
    ? transactions.filter((transaction) => transaction.needs_review)
    : transactions;

  return (
    <main className="page-shell">
      <header className="hero">
        <p className="eyebrow">Independent designer workspace</p>
        <h1>Statement<br />Categorizer</h1>
        <p className="intro">Sort business transactions before tax time. The rules show their work and leave uncertain purchases for you.</p>
        <label className="upload-button">
          <span>{isLoading ? "Reading statement..." : "Upload CSV statement"}</span>
          <input type="file" accept=".csv,text/csv" onChange={handleUpload} disabled={isLoading} />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
      </header>

      {summary && (
        <section className="results" aria-live="polite">
          <div className="summary-grid">
            <div><span>Spending</span><strong>${summary.spending_total}</strong></div>
            <div><span>Needs review</span><strong>${summary.review_total}</strong></div>
            <div><span>Refunds</span><strong>${summary.refund_total}</strong></div>
            <div><span>Transfers</span><strong>${summary.transfer_total}</strong></div>
          </div>
          <div className="review-heading">
            <div>
              <p className="eyebrow">Review queue</p>
              <h2>{summary.review_count} of {summary.transaction_count} transactions need your call</h2>
            </div>
            <div className="actions">
              <button type="button" className="filter-button" onClick={() => setShowReviewOnly((current) => !current)}>
                {showReviewOnly ? "Show all" : "Needs review only"}
              </button>
              <button type="button" className="filter-button" onClick={exportTransactions}>Export CSV</button>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Date</th><th>Description</th><th>Amount</th><th>Category</th><th>Why</th></tr></thead>
              <tbody>
                {visibleTransactions.map((transaction) => (
                  <tr key={transaction.source_row} className={transaction.needs_review ? "needs-review" : ""}>
                    <td>{transaction.date}</td>
                    <td>{transaction.description}</td>
                    <td>${transaction.amount}</td>
                    <td>
                      <select
                        className="category-select"
                        value={transaction.category}
                        aria-label={`Category for ${transaction.description}`}
                        onChange={(event) => updateCategory(transaction.source_row, event.target.value)}
                      >
                        {CATEGORIES.map((category) => <option key={category}>{category}</option>)}
                      </select>
                    </td>
                    <td>{transaction.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
