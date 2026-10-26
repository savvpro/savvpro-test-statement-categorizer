import { useState } from "react";
import "./App.css";

const API = "http://127.0.0.1:8000";

const expenseCategories = [
  "Software",
  "Travel",
  "Internet",
  "Office Supplies",
  "Other Business Expense",
];

function categoriesFor(type) {
  if (type === "expense" || type === "refund") return expenseCategories;
  if (type === "income") return ["Client Income"];
  if (type === "transfer") return ["Transfer"];
  return ["Needs Review"];
}

async function readResponse(response) {
  const body = await response.json();

  if (!response.ok) {
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : "Request failed. Check your selections and try again."
    );
  }

  return body;
}

function TransactionRow({ row, onSave, busy }) {
  const [type, setType] = useState(row.type);
  const [category, setCategory] = useState(row.category);

  // Preserve an unresolved refund category until the user selects one.
  const choices = [...new Set([...categoriesFor(type), category])];

  function changeType(event) {
    const nextType = event.target.value;
    setType(nextType);
    setCategory(categoriesFor(nextType)[0]);
  }

  return (
    <tr className={row.needs_review ? "review-row" : ""}>
      <td>{row.date}</td>
      <td>
        <strong>{row.description}</strong>
        <small>{row.reason}</small>
      </td>
      <td className="amount">{row.amount}</td>
      <td>
        <select
          aria-label={`Type for ${row.description}`}
          value={type}
          onChange={changeType}
          disabled={busy}
        >
          {["expense", "income", "refund", "transfer", "unknown"].map(
            (value) => (
              <option key={value} value={value}>
                {value}
              </option>
            )
          )}
        </select>
      </td>
      <td>
        <select
          aria-label={`Category for ${row.description}`}
          value={category}
          onChange={(event) => setCategory(event.target.value)}
          disabled={busy}
        >
          {choices.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </td>
      <td>
        <span className={row.needs_review ? "badge warning" : "badge"}>
          {row.needs_review ? "Needs Review" : "Categorized"}
        </span>
      </td>
      <td>
        <button
          disabled={busy}
          onClick={() => onSave(row.id, type, category)}
        >
          Save
        </button>
      </td>
    </tr>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [statement, setStatement] = useState(null);
  const [reviewOnly, setReviewOnly] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function upload(event) {
    event.preventDefault();
    if (!file || busy) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const form = new FormData();
      form.append("file", file);

      const response = await fetch(`${API}/statements`, {
        method: "POST",
        body: form,
      });

      const data = await readResponse(response);
      setStatement(data);
      setReviewOnly(false);
      setMessage("Statement uploaded and categorized.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function saveCorrection(id, type, category) {
    if (!statement || busy) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API}/statements/${statement.statement_id}/transactions/${id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type, category }),
        }
      );

      const data = await readResponse(response);
      setStatement(data);
      setMessage(`Transaction ${id} saved. Totals updated.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function exportCSV() {
    if (!statement) return;

    const columns = [
      "date",
      "description",
      "amount",
      "currency",
      "type",
      "category",
      "needs_review",
      "reason",
    ];

    function csvCell(value, column) {
      let text = String(value ?? "");

      // Prevent text fields from being interpreted as spreadsheet formulas.
      if (column !== "amount" && /^[\s]*[=+\-@]/.test(text)) {
        text = "'" + text;
      }

      return `"${text.replaceAll('"', '""')}"`;
    }

    const lines = [
      columns.join(","),
      ...statement.transactions.map((row) =>
        columns.map((column) => csvCell(row[column], column)).join(",")
      ),
    ];

    const blob = new Blob(["\uFEFF" + lines.join("\r\n")], {
      type: "text/csv;charset=utf-8;",
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "categorized-statement.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  const summary = statement?.summary;
  const visibleRows =
    statement?.transactions.filter(
      (row) => !reviewOnly || row.needs_review
    ) ?? [];

  return (
    <main>
      <header>
        <span className="eyebrow">FOR FREELANCE DESIGNERS</span>
        <h1>Statement Categorizer</h1>
        <p>
          Organize business transactions, review uncertain matches, and
          export your results.
        </p>
      </header>

      <section className="panel">
        <h2>Upload a statement</h2>
        <p>
          Use a fake UTF-8 CSV with date, description, amount, and currency
          columns. Negative amounts are outgoing; positive amounts are
          incoming. Maximum 2 MB and 5,000 rows.
        </p>
        <form onSubmit={upload}>
          <label htmlFor="statement-file">CSV statement</label>
          <input
            id="statement-file"
            type="file"
            accept=".csv"
            disabled={busy}
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <button type="submit" disabled={!file || busy}>
            {busy ? "Working…" : "Upload and categorize"}
          </button>
        </form>
        <small>
          Demo storage is temporary. Restarting the backend clears uploaded
          statements. Export your saved results before closing.
        </small>
      </section>

      {error && <p className="error" role="alert">{error}</p>}
      {message && <p className="success" role="status">{message}</p>}

      {statement && (
        <>
          <section className="cards" aria-label="Statement summary">
            <article className="card">
              <span>Income</span>
              <strong>{summary.currency} {summary.total_income}</strong>
            </article>
            <article className="card">
              <span>Net categorized expenses</span>
              <strong>{summary.currency} {summary.net_expenses}</strong>
            </article>
            <article className="card">
              <span>Refunds included in net expenses</span>
              <strong>{summary.currency} {summary.total_refunds}</strong>
            </article>
            <article className="card">
              <span>Needs review</span>
              <strong>{summary.needs_review_count} transactions</strong>
            </article>
          </section>

          <section className="panel">
            <h2>Expense breakdown</h2>
            <div className="breakdown">
              {Object.entries(summary.category_net_expenses).map(
                ([category, total]) => (
                  <div key={category}>
                    <span>{category}</span>
                    <strong>{summary.currency} {total}</strong>
                  </div>
                )
              )}
            </div>
            <p>
              Transfers excluded: incoming {summary.transfers_in},
              outgoing {summary.transfers_out} {summary.currency}.
            </p>
            <p>
              Unresolved amounts excluded: incoming{" "}
              {summary.unresolved_incoming}, outgoing{" "}
              {summary.unresolved_outgoing} {summary.currency}.
            </p>
          </section>

          <section className="panel">
            <div className="toolbar">
              <h2>Transactions ({statement.transaction_count})</h2>
              <button onClick={exportCSV} disabled={busy}>
                Export saved results
              </button>
            </div>

            <label className="filter">
              <input
                type="checkbox"
                checked={reviewOnly}
                onChange={(event) => setReviewOnly(event.target.checked)}
              />
              Show only Needs Review
            </label>

            <p>
              Review each transaction’s business purpose. Select a type and
              category, then click Save. Totals and exports use saved values.
            </p>

            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Description and reason</th>
                    <th>Amount ({summary.currency})</th>
                    <th>Type</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.map((row) => (
                    <TransactionRow
                      key={`${statement.statement_id}-${row.id}-${row.type}-${row.category}`}
                      row={row}
                      onSave={saveCorrection}
                      busy={busy}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            {visibleRows.length === 0 && (
              <p>No transactions need review.</p>
            )}
          </section>
        </>
      )}
    </main>
  );
}