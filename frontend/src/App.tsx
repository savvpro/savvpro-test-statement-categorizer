import { useState, useCallback, useRef } from "react";
import {
  Transaction,
  UploadResponse,
  TransactionUpdate,
} from "./types";
import {
  uploadCsv,
  updateTransaction,
  exportCsv,
  downloadCsv,
} from "./services/api";

const CATEGORIES = [
  "Software",
  "Travel",
  "Meals",
  "Office Supplies",
  "Marketing",
  "Utilities",
  "Subscriptions",
  "Income",
  "Refund",
  "Transfer",
  "Needs Review",
];

function getBadgeClass(category: string): string {
  return `category-badge badge-${category.toLowerCase().replace(/\s+/g, "-")}`;
}

function getConfidenceClass(confidence: number): string {
  if (confidence >= 0.8) return "confidence-high";
  if (confidence >= 0.5) return "confidence-medium";
  return "confidence-low";
}

function formatCurrency(amount: number): string {
  const abs = Math.abs(amount);
  const sign = amount < 0 ? "-" : amount > 0 ? "+" : "";
  return `${sign}$${abs.toFixed(2)}`;
}

export default function App() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      setLoading(true);
      setError(null);
      try {
        const result: UploadResponse = await uploadCsv(file);
        setTransactions(result.transactions);
        setSummary(result.summary);
        setWarnings(result.warnings);
        setUploadSuccess(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const handleFix = useCallback(
    async (id: string, category: string) => {
      setLoading(true);
      try {
        const update: TransactionUpdate = { category };
        const result = await updateTransaction(id, update);
        setTransactions((prev) =>
          prev.map((t) =>
            t.id === id ? result.transaction : t
          )
        );
        setSummary(result.summary);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Update failed");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const handleExport = useCallback(async () => {
    try {
      const blob = await exportCsv();
      downloadCsv(blob);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
    }
  }, []);

  const needsReviewCount = transactions.filter(
    (t) => t.needs_review
  ).length;

  return (
    <div className="app">
      <div className="header">
        <h1>Statement Categorizer</h1>
        <p>Upload your business credit card statement to categorize transactions for tax time.</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="upload-area" onClick={() => fileInput.current?.click()}>
        <input
          ref={fileInput}
          type="file"
          accept=".csv"
          onChange={(e) => {
            if (e.target.files?.[0]) handleUpload(e.target.files[0]);
          }}
          style={{ display: "none" }}
        />
        {loading ? (
          <>
            <div className="spinner"></div>
            <p>Processing statement...</p>
          </>
        ) : uploadSuccess ? (
          <p>Statement processed successfully.</p>
        ) : (
          <>
            <p>Drag & drop a CSV file or click to browse</p>
            <p>Supported: single Amount column or Debit/Credit columns</p>
          </>
        )}
      </div>

      {warnings.length > 0 && (
        <div className="warnings-list">
          <h4>⚠️ {warnings.length} warning(s) during parsing</h4>
          <ul>
            {warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {transactions.length > 0 ? (
        <>
          <div className="summary-panel">
            <div className="summary-item total">
              <span className="label">Total Spend</span>
              <span className="value">
                {formatCurrency(
                  Object.entries(summary).reduce(
                    (acc, [cat, amt]) =>
                      cat !== "Transfer" ? acc + amt : acc,
                    0
                  )
                )}
              </span>
            </div>
            <div className="summary-item needs-review">
              <span className="label">Needs Review</span>
              <span className="value">
                {formatCurrency(summary["Needs Review"] || 0)}
              </span>
            </div>
            <div className="summary-item refund">
              <span className="label">Refunds</span>
              <span className="value">
                {formatCurrency(summary["Refund"] || 0)}
              </span>
            </div>
          </div>

          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th>Amount</th>
                  <th>Category</th>
                  <th>Confidence</th>
                  <th>Reason</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((tx) => (
                  <tr
                    key={tx.id}
                    className={
                      (tx.needs_review ? "needs-review" : "") +
                      (tx.is_duplicate ? " duplicate" : "")
                    }
                  >
                    <td>{tx.date}</td>
                    <td>
                      {tx.description}
                      {tx.is_duplicate && (
                        <span style={{ marginLeft: 8, color: "#c62828", fontSize: "11px" }}>
                          ⚠ Duplicate
                        </span>
                      )}
                    </td>
                    <td>
                      <span className={`amount ${tx.amount < 0 ? "negative" : "positive"}`}>
                        {formatCurrency(tx.amount)}
                      </span>
                    </td>
                    <td>
                      <span className={getBadgeClass(tx.category)}>
                        {tx.category}
                      </span>
                    </td>
                    <td>
                      <span className={getConfidenceClass(tx.confidence)}>
                        {(tx.confidence * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td>
                      <span className="reason">{tx.reason}</span>
                    </td>
                    <td>
                      {tx.needs_review ? (
                        <select
                          value={tx.category}
                          onChange={(e) =>
                            handleFix(tx.id, e.target.value)}
                        >
                          {CATEGORIES.map((cat) => (
                            <option key={cat} value={cat}>
                              {cat}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span style={{ color: "#6e6e73", fontSize: "12px" }}>
                          —
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="button-group">
            <button
              className="btn btn-outline"
              onClick={handleExport}
              disabled={loading}
            >
              📥 Export CSV
            </button>
            <span style={{ color: "#6e6e73", fontSize: "13px" }}>
              {needsReviewCount} transaction(s) need review
            </span>
          </div>
        </>
      ) : (
        <div className="empty-state">
          <h3>No statement uploaded yet</h3>
          <p>Upload a CSV to get started.</p>
        </div>
      )}
    </div>
  );
}
