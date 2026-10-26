import { useEffect, useState } from "react";
import { fetchCategories, fetchSummary, uploadStatement } from "./api";
import UploadForm from "./components/UploadForm.jsx";
import SummaryPanel from "./components/SummaryPanel.jsx";
import TransactionTable from "./components/TransactionTable.jsx";
import { downloadCsv } from "./exportCsv";

export default function App() {
  const [categories, setCategories] = useState([]);
  const [rows, setRows] = useState([]);
  const [skipped, setSkipped] = useState([]);
  const [summary, setSummary] = useState(null);
  const [onlyReview, setOnlyReview] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchCategories().then(setCategories).catch(() => setError("Cannot reach the server. Is the backend running?"));
  }, []);

  async function handleUpload(file, chargesArePositive) {
    setBusy(true);
    setError("");
    try {
      const data = await uploadStatement(file, chargesArePositive);
      setRows(data.rows);
      setSkipped(data.errors);
      setSummary(data.summary);
      setOnlyReview(false);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  // Fixing one row also fixes every row from the same merchant.
  async function handleChange(row, category) {
    const next = rows.map((r) =>
      r.merchant === row.merchant
        ? { ...r, category, status: "ok", reason: "Set by you.", refund_of: category === "Refund" ? r.refund_of : null }
        : r
    );
    setRows(next);
    try {
      setSummary(await fetchSummary(next));
    } catch (e) {
      setError(e.message);
    }
  }

  const visible = onlyReview ? rows.filter((r) => r.category === "Needs Review") : rows;

  return (
    <main>
      <header>
        <h1>Statement categorizer</h1>
        <p>Upload a business card statement. Every purchase is sorted for tax time, and anything unclear is left for you.</p>
      </header>

      <UploadForm onUpload={handleUpload} busy={busy} />
      {error && <p role="alert" className="error">{error}</p>}

      {rows.length > 0 && (
        <section className="results">
          <SummaryPanel summary={summary} onShowReview={() => setOnlyReview(true)} />
          <div>
            <div className="toolbar">
              <button className="link" onClick={() => setOnlyReview(!onlyReview)}>
                {onlyReview ? "Show all rows" : "Show only rows that need review"}
              </button>
              <button className="link" onClick={() => downloadCsv(rows)}>Download sorted CSV</button>
            </div>
            {skipped.length > 0 && (
              <p className="skipped">
                Skipped {skipped.length} unreadable {skipped.length === 1 ? "row" : "rows"}:{" "}
                {skipped.map((s) => `row ${s.row_number} (${s.reason})`).join("; ")}.
              </p>
            )}
            <TransactionTable rows={visible} categories={categories} onChange={handleChange} />
          </div>
        </section>
      )}
    </main>
  );
}
