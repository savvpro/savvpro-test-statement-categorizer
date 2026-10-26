import { useState } from "react";
import { correctTransaction, setLoan, uploadStatement } from "./api";
import LoanFields, { buildLoan, useLoanFields } from "./components/LoanFields";
import ReviewPanel from "./components/ReviewPanel";
import SummaryPanel from "./components/SummaryPanel";
import TransactionTable from "./components/TransactionTable";

export default function App() {
  const [statement, setStatement] = useState(null);
  const [file, setFile] = useState(null);
  const [hasLoan, setHasLoan] = useState(false);
  const [loanFields, setLoanFields] = useLoanFields();
  const [lateLoanFields, setLateLoanFields] = useLoanFields();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  // Run any API call with shared loading and error handling.
  async function run(action) {
    setBusy(true);
    setError("");
    try {
      setStatement(await action());
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  const onUpload = (e) => {
    e.preventDefault();
    if (!file) return setError("Choose a .csv file first.");
    run(() => uploadStatement(file, hasLoan ? buildLoan(loanFields) : null));
  };

  const onCorrect = (id, category) =>
    run(() => correctTransaction(statement.id, id, category));

  const onAddLoan = (e) => {
    e.preventDefault();
    run(() => setLoan(statement.id, buildLoan(lateLoanFields)));
  };

  return (
    <main>
      <h1>Landlord Statement Categorizer</h1>
      <p className="hint">
        Upload a bank statement. Rules, not AI, decide each category, and anything
        uncertain is left for you to review.
      </p>

      <form className="card" onSubmit={onUpload}>
        <h2>1. Upload</h2>
        <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0] || null)} />
        <label className="check">
          <input type="checkbox" checked={hasLoan} onChange={(e) => setHasLoan(e.target.checked)} />
          I have a mortgage (split payments into interest and principal)
        </label>
        {hasLoan && <LoanFields fields={loanFields} onChange={setLoanFields} />}
        <button disabled={busy}>{busy ? "Working…" : "Categorize"}</button>
      </form>

      {error && <div className="error" role="alert">{error}</div>}

      {statement && (
        <>
          <p className="hint">
            {statement.filename}: {statement.transactions.length} rows loaded
            {statement.parse_errors.length > 0 &&
              `, ${statement.parse_errors.length} skipped as unreadable`}
          </p>

          {statement.parse_errors.length > 0 && (
            <details className="card">
              <summary>Skipped rows</summary>
              <ul>
                {statement.parse_errors.map((p, i) => (
                  <li key={i}>{JSON.stringify(p)}</li>
                ))}
              </ul>
            </details>
          )}

          {!statement.loan && (
            <form className="card" onSubmit={onAddLoan}>
              <h2>Add mortgage details</h2>
              <p className="hint">Mortgage rows are waiting for these to be split.</p>
              <LoanFields fields={lateLoanFields} onChange={setLateLoanFields} />
              <button disabled={busy}>Split mortgage payments</button>
            </form>
          )}

          <ReviewPanel transactions={statement.transactions} onCorrect={onCorrect} busy={busy} />
          <SummaryPanel summary={statement.summary} />
          <TransactionTable transactions={statement.transactions} />
        </>
      )}
    </main>
  );
}