import { useRef, useState } from "react";
import { categorizeStatement } from "./api";
import type {
  CategorizeResponse,
  DisplayTransaction,
  InvalidRow,
} from "./types";

const CATEGORIES = [
  "Income",
  "Groceries",
  "Dining",
  "Transport",
  "Shopping",
  "Bills",
  "Healthcare",
  "Transfers",
  "Software",
  "Other",
  "Needs Review",
];

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

function formatMoney(amount: number): string {
  return currency.format(amount);
}

function App() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [transactions, setTransactions] = useState<DisplayTransaction[]>([]);
  const [invalidRows, setInvalidRows] = useState<InvalidRow[]>([]);
  const [fileName, setFileName] = useState("");
  const [totalRows, setTotalRows] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  async function uploadFile(file?: File) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setError("Please choose a CSV file.");
      return;
    }

    setError("");
    setIsLoading(true);
    setFileName(file.name);
    try {
      const result: CategorizeResponse = await categorizeStatement(file);
      setTransactions(
        result.transactions.map((transaction) => ({
          ...transaction,
          reviewedByUser: false,
        })),
      );
      setInvalidRows(result.invalid_rows);
      setTotalRows(result.total_rows);
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : "Something went wrong while processing the statement.",
      );
      setTransactions([]);
      setInvalidRows([]);
      setTotalRows(0);
    } finally {
      setIsLoading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function changeCategory(rowNumber: number, category: string) {
    setTransactions((current) =>
      current.map((transaction) =>
        transaction.row_number === rowNumber
          ? { ...transaction, category }
          : transaction,
      ),
    );
  }

  function markReviewed(rowNumber: number) {
    setTransactions((current) =>
      current.map((transaction) =>
        transaction.row_number === rowNumber
          ? {
              ...transaction,
              needs_review: false,
              review_reason: null,
              reviewedByUser: true,
            }
          : transaction,
      ),
    );
  }

  const needsReviewCount = transactions.filter(
    (transaction) => transaction.needs_review,
  ).length;
  const reviewedCount = transactions.filter(
    (transaction) => transaction.reviewedByUser,
  ).length;
  const totals = transactions.reduce<Record<string, { amount: number; count: number }>>(
    (result, transaction) => {
      const entry = result[transaction.category] ?? { amount: 0, count: 0 };
      result[transaction.category] = {
        amount: entry.amount + transaction.amount,
        count: entry.count + 1,
      };
      return result;
    },
    {},
  );
  const sortedTotals = Object.entries(totals).sort(([left], [right]) =>
    left.localeCompare(right),
  );
  const hasStatement = fileName !== "" && !isLoading && !error;

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="#" aria-label="Ledgerly home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path
                d="M5 18V9.5L12 5l7 4.5V18M9 18v-5h6v5M3.5 19h17"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </span>
          <span>ledgerly</span>
        </a>
        <div className="topbar-note">
          <span className="privacy-dot" />
          Private by design
        </div>
      </header>

      <section className="intro">
        <div className="eyebrow">
          <span className="eyebrow-line" />
          YOUR MONEY, ORGANIZED
        </div>
        <h1>
          Tax time, <span>sorted.</span>
        </h1>
        <p>
          Drop in a statement. We’ll sort the familiar, flag the unusual, and
          leave the final call to you.
        </p>
      </section>

      <section className="upload-panel" aria-labelledby="upload-title">
        <div
          className={`dropzone${isDragging ? " is-dragging" : ""}${isLoading ? " is-loading" : ""}`}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setIsDragging(false);
            void uploadFile(event.dataTransfer.files[0]);
          }}
        >
          <div className="upload-icon" aria-hidden="true">
            {isLoading ? (
              <span className="spinner" />
            ) : (
              <svg viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5M5 15.5v3A1.5 1.5 0 006.5 20h11a1.5 1.5 0 001.5-1.5v-3"
                  stroke="currentColor"
                  strokeWidth="1.7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </div>
          <h2 id="upload-title">
            {isLoading ? "Reading your statement…" : "Bring in a statement"}
          </h2>
          <p>
            {isLoading
              ? "Matching transactions to clear, sensible categories."
              : "Drag and drop a CSV file here, or browse your files."}
          </p>
          {!isLoading && (
            <button
              className="button button-primary"
              type="button"
              onClick={() => inputRef.current?.click()}
            >
              <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
                <path
                  d="M10 13V4m0 0L6.5 7.5M10 4l3.5 3.5M4.5 12.5v2A1.5 1.5 0 006 16h8a1.5 1.5 0 001.5-1.5v-2"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Choose a file
            </button>
          )}
          <span className="file-hint">CSV files only · Your data stays yours</span>
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv"
            className="visually-hidden"
            onChange={(event) => void uploadFile(event.target.files?.[0])}
          />
        </div>
        {error && (
          <div className="alert alert-error" role="alert">
            <span className="alert-icon" aria-hidden="true">!</span>
            <div>
              <strong>We couldn’t read that statement</strong>
              <p>{error}</p>
            </div>
            <button
              className="alert-dismiss"
              type="button"
              aria-label="Dismiss error"
              onClick={() => setError("")}
            >
              ×
            </button>
          </div>
        )}
      </section>

      {hasStatement && (
        <>
          <section className="summary-section" aria-label="Statement summary">
            <div className="section-heading">
              <div>
                <div className="eyebrow">
                  <span className="eyebrow-line" />
                  YOUR OVERVIEW
                </div>
                <h2>Looking good.</h2>
              </div>
              <span className="statement-name">
                <svg viewBox="0 0 18 18" fill="none" aria-hidden="true">
                  <path
                    d="M5 2.75h5.5l3.5 3.5v9H5a1 1 0 01-1-1v-10a1 1 0 011-1zM10 3v4h4M6.5 10h5M6.5 12.5h5"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <span>{fileName}</span>
              </span>
            </div>

            <div className="stat-grid">
              <article className="stat-card">
                <span className="stat-label">Transactions</span>
                <strong>{transactions.length}</strong>
                <span className="stat-caption">
                  {totalRows === transactions.length
                    ? "All rows read"
                    : `${totalRows} rows in statement`}
                </span>
              </article>
              <article
                className={`stat-card${needsReviewCount ? " stat-card-review" : ""}`}
              >
                <span className="stat-label">Needs your eye</span>
                <strong>{needsReviewCount}</strong>
                <span className="stat-caption">
                  {needsReviewCount
                    ? "A few we weren’t sure about"
                    : "Everything has a category"}
                </span>
              </article>
              <article className="stat-card">
                <span className="stat-label">Rows reviewed</span>
                <strong>{reviewedCount}</strong>
                <span className="stat-caption">Confirmed by you</span>
              </article>
            </div>
          </section>

          <section className="totals-section" aria-labelledby="totals-title">
            <div className="section-heading compact-heading">
              <div>
                <div className="eyebrow">
                  <span className="eyebrow-line" />
                  THE BREAKDOWN
                </div>
                <h2 id="totals-title">Where it’s going</h2>
              </div>
              <span className="subtle-caption">Net totals · USD</span>
            </div>
            {sortedTotals.length ? (
              <div className="totals-grid">
                {sortedTotals.map(([category, total], index) => (
                  <article className="total-card" key={category}>
                    <div className={`total-dot tone-${index % 6}`} />
                    <div className="total-info">
                      <span className="total-name">{category}</span>
                      <span className="total-count">
                        {total.count} {total.count === 1 ? "transaction" : "transactions"}
                      </span>
                    </div>
                    <strong className={total.amount > 0 ? "amount-positive" : ""}>
                      {formatMoney(total.amount)}
                    </strong>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state">
                No valid transactions to summarize. Review the invalid rows below.
              </div>
            )}
          </section>

          <section className="transactions-section" aria-labelledby="transactions-title">
            <div className="section-heading compact-heading">
              <div>
                <div className="eyebrow">
                  <span className="eyebrow-line" />
                  TRANSACTION LIST
                </div>
                <h2 id="transactions-title">Every little detail</h2>
              </div>
              <span className="table-count">
                {transactions.length} {transactions.length === 1 ? "transaction" : "transactions"}
              </span>
            </div>

            {transactions.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Date</th>
                      <th scope="col">Description</th>
                      <th scope="col">Amount</th>
                      <th scope="col">Category</th>
                      <th scope="col">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map((transaction) => (
                      <tr
                        className={transaction.needs_review ? "needs-review-row" : ""}
                        key={transaction.row_number}
                      >
                        <td className="date-cell">{transaction.date}</td>
                        <td className="description-cell">
                          <span>{transaction.description}</span>
                          {transaction.review_reason && transaction.needs_review && (
                            <span className="review-reason">
                              {transaction.review_reason}
                            </span>
                          )}
                          {transaction.transaction_type !== "purchase" &&
                            transaction.transaction_type !== "unknown" && (
                              <span className="transaction-type">
                                {transaction.transaction_type}
                              </span>
                            )}
                        </td>
                        <td
                          className={`amount-cell${transaction.amount > 0 ? " amount-positive" : ""}`}
                        >
                          {formatMoney(transaction.amount)}
                        </td>
                        <td>
                          <select
                            className={`category-select${transaction.needs_review ? " category-select-review" : ""}`}
                            aria-label={`Category for ${transaction.description}`}
                            value={transaction.category}
                            onChange={(event) =>
                              changeCategory(transaction.row_number, event.target.value)
                            }
                          >
                            {[...new Set([...CATEGORIES, transaction.category])].map(
                              (category) => (
                                <option value={category} key={category}>
                                  {category}
                                </option>
                              ),
                            )}
                          </select>
                        </td>
                        <td>
                          {transaction.needs_review ? (
                            <button
                              className="status-badge status-review status-button"
                              type="button"
                              onClick={() => markReviewed(transaction.row_number)}
                              aria-label={`Mark ${transaction.description} reviewed`}
                              title="Mark as reviewed"
                            >
                              <span className="status-dot" />
                              Needs review
                              <span className="check-icon" aria-hidden="true">✓</span>
                            </button>
                          ) : transaction.reviewedByUser ? (
                            <span className="status-badge status-reviewed">
                              <span className="status-dot" />
                              Reviewed
                            </span>
                          ) : (
                            <span className="status-badge status-categorized">
                              <span className="status-dot" />
                              Categorized
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="empty-state">
                No valid transactions were found in this statement.
              </div>
            )}
          </section>

          {invalidRows.length > 0 && (
            <section className="invalid-section" aria-labelledby="invalid-title">
              <div className="invalid-heading">
                <div>
                  <div className="eyebrow">
                    <span className="eyebrow-line" />
                    COULDN’T READ {invalidRows.length}{" "}
                    {invalidRows.length === 1 ? "ROW" : "ROWS"}
                  </div>
                  <h2 id="invalid-title">A couple of loose ends</h2>
                </div>
                <span className="invalid-caption">These rows weren’t included above</span>
              </div>
              <div className="invalid-list">
                {invalidRows.map((row) => (
                  <details className="invalid-item" key={row.row_number}>
                    <summary>
                      <span className="invalid-row-number">Row {row.row_number}</span>
                      <span>{row.errors.join(" ")}</span>
                      <span className="details-hint">Details</span>
                    </summary>
                    <pre>{JSON.stringify(row.row_data, null, 2)}</pre>
                  </details>
                ))}
              </div>
            </section>
          )}
        </>
      )}

      <footer className="footer">
        <span>Made for a little more peace of mind.</span>
        <span>
          Private by design <span className="footer-divider">·</span> Rules, not AI
        </span>
      </footer>
    </main>
  );
}

export default App;
