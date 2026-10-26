import { useCallback, useState } from "react";
import { categorize } from "./api.js";
import { money, toCsv } from "./format.js";
import Summary from "./components/Summary.jsx";
import TransactionTable from "./components/TransactionTable.jsx";

export default function App() {
  const [file, setFile] = useState(null);
  const [positiveIsCharge, setPositiveIsCharge] = useState(false);
  const [overrides, setOverrides] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const run = useCallback(
    async (nextFile, nextOverrides, nextPositive) => {
      setLoading(true);
      setError("");
      try {
        setResult(await categorize(nextFile, { positiveIsCharge: nextPositive, overrides: nextOverrides }));
      } catch (e) {
        setError(e.message);
        setResult(null);
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const onSubmit = (event) => {
    event.preventDefault();
    if (!file) return;
    setOverrides({});
    run(file, {}, positiveIsCharge);
  };

  const onFix = (merchantKey, category) => {
    const next = { ...overrides, [merchantKey]: category };
    setOverrides(next);
    run(file, next, positiveIsCharge);
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([toCsv(result.transactions)], { type: "text/csv" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "categorized-statement.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <main>
      <header>
        <h1>Freelancer Statement Categorizer</h1>
        <p>Upload a business card or bank statement (CSV). Every row is sorted for tax time. Anything uncertain is left for you.</p>
      </header>

      <form onSubmit={onSubmit} className="card upload">
        <input type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files[0] ?? null)} aria-label="Statement CSV" />
        <label>
          <input type="checkbox" checked={positiveIsCharge} onChange={(e) => setPositiveIsCharge(e.target.checked)} />
          Purchases are shown as positive numbers (common for credit cards)
        </label>
        <button type="submit" disabled={!file || loading}>{loading ? "Working…" : "Categorize"}</button>
      </form>

      {error && <p role="alert" className="error">{error}</p>}

      {result && (
        <>
          {result.warnings.map((w) => (
            <p key={w} className="warning">{w}</p>
          ))}
          {result.issues.length > 0 && (
            <details className="card">
              <summary>{result.issues.length} row(s) could not be read and were skipped</summary>
              <ul>
                {result.issues.map((i) => (
                  <li key={i.line}>Line {i.line}: {i.message}</li>
                ))}
              </ul>
            </details>
          )}
          <Summary summary={result.summary} />
          <div className="toolbar">
            <h2>Transactions ({result.transactions.length})</h2>
            <button type="button" className="secondary" onClick={download}>Export CSV</button>
          </div>
          <TransactionTable
            transactions={result.transactions}
            categories={result.categories}
            onFix={onFix}
            busy={loading}
            money={money}
          />
        </>
      )}
    </main>
  );
}
