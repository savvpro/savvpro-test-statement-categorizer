import { useCallback, useEffect, useRef, useState } from "react";
import { categorize, getCategories } from "./api";
import UploadPanel from "./components/Uploadpanel";
import Summary from "./components/Summary";
import TransactionTable from "./components/TransactionTable";
import { downloadCsv } from "./utils";
import "./App.css";

const OFFLINE = "Cannot reach the server. Is the backend running on port 8000?";

export default function App() {
  const [categories, setCategories] = useState([]);
  const [file, setFile] = useState(null);
  const [chargesPositive, setChargesPositive] = useState(false);
  const [userRules, setUserRules] = useState({});
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const latest = useRef(0); // ignore responses from outdated requests

  useEffect(() => {
    getCategories()
      .then((r) => setCategories(r.categories))
      .catch(() => setError(OFFLINE));
  }, []);

  const run = useCallback(async (f, flip, rules) => {
    const id = ++latest.current;
    setLoading(true);
    setError("");
    try {
      const result = await categorize(f, flip, rules);
      if (id === latest.current) setData(result);
    } catch (e) {
      if (id === latest.current) setError(e instanceof TypeError ? OFFLINE : e.message);
    } finally {
      if (id === latest.current) setLoading(false);
    }
  }, []);

  function handleUpload(f, flip) {
    setFile(f);
    setChargesPositive(flip);
    setUserRules({});
    setData(null);
    run(f, flip, {});
  }

  // A fix applies to every row of the same merchant, so we re-run the whole
  // statement with the new rule and let the backend recompute everything.
  function handleFix(merchantKey, category) {
    const next = { ...userRules, [merchantKey]: category };
    setUserRules(next);
    run(file, chargesPositive, next);
  }

  return (
    <main className="app">
      <header>
        <h1>Statement Categorizer</h1>
        <p className="muted">
          Upload a CSV statement. Every row is sorted by plain rules. When the app is
          not sure, it asks you.
        </p>
      </header>

      <UploadPanel onUpload={handleUpload} loading={loading} />

      {error && <div className="error" role="alert">{error}</div>}

      {data && (
        <>
          <Summary summary={data.summary} />

          {data.skipped.length > 0 && (
            <details className="skipped">
              <summary>{data.skipped.length} row(s) could not be read</summary>
              <ul>
                {data.skipped.map((s) => (
                  <li key={s.row}>Line {s.row}: {s.error}</li>
                ))}
              </ul>
            </details>
          )}

          <div className="toolbar">
            <h2>Transactions</h2>
            <button className="secondary" onClick={() => downloadCsv(data.rows)}>
              Download CSV
            </button>
          </div>
          <TransactionTable
            rows={data.rows}
            categories={categories}
            onFix={handleFix}
            busy={loading}
          />
        </>
      )}
    </main>
  );
}