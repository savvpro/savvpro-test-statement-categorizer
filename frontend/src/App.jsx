import { useEffect, useMemo, useRef, useState } from "react";

const REVIEW = "Needs Review";
const NOTES = { Transfer: "not spending", Income: "money in", Refund: "money back" };

async function readError(res, fallback) {
  const data = await res.json().catch(() => null);
  return typeof data?.detail === "string" ? data.detail : fallback;
}

export default function App() {
  const [categories, setCategories] = useState([]);
  const [rows, setRows] = useState([]);
  const [rowErrors, setRowErrors] = useState([]);
  const [totals, setTotals] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [onlyReview, setOnlyReview] = useState(false);
  const latestRequest = useRef(0);

  useEffect(() => {
    fetch("/api/categories")
      .then((r) => r.json())
      .then((d) => setCategories(d.categories))
      .catch(() => setError("Cannot reach the server. Is the backend running?"));
  }, []);

  async function handleUpload(event) {
    const input = event.target;
    const file = input.files[0];
    if (!file) return;
    setLoading(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    try {
      const res = await fetch("/api/upload", { method: "POST", body: form });
      if (!res.ok) throw new Error(await readError(res, "Upload failed"));
      const data = await res.json();
      setRows(data.rows);
      setRowErrors(data.errors);
      setTotals(data.totals);
      setOnlyReview(false);
    } catch (err) {
      setRows([]);
      setRowErrors([]);
      setTotals({});
      setError(err.message || "Upload failed");
    } finally {
      setLoading(false);
      input.value = ""; // allow re-uploading the same file
    }
  }

  async function changeCategory(id, category) {
    const next = rows.map((r) =>
      r.id === id ? { ...r, category, needs_review: category === REVIEW, edited: true } : r
    );
    setRows(next);
    const requestId = ++latestRequest.current;
    try {
      const res = await fetch("/api/totals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows: next.map((r) => ({ amount: r.amount, category: r.category })) }),
      });
      if (!res.ok) throw new Error();
      const data = await res.json();
      if (requestId === latestRequest.current) setTotals(data.totals); // ignore stale replies
    } catch {
      setError("Could not update totals. Please try again.");
    }
  }

  const reviewCount = useMemo(() => rows.filter((r) => r.needs_review).length, [rows]);
  const visible = onlyReview ? rows.filter((r) => r.needs_review) : rows;

  return (
    <main className="page">
      <h1>Statement Categorizer</h1>
      <p className="muted">
        Upload a CSV with <code>date, description, amount</code>. Anything the app is not sure about
        goes to <strong>Needs Review</strong>.
      </p>

      <label className="upload">
        {loading ? "Reading statement..." : "Choose CSV file"}
        <input type="file" accept=".csv" onChange={handleUpload} disabled={loading} />
      </label>

      {error && <div className="alert" role="alert">{error}</div>}

      {rowErrors.length > 0 && (
        <div className="alert warn">
          <strong>{rowErrors.length} row(s) skipped:</strong>
          <ul>
            {rowErrors.map((e) => (
              <li key={e.line}>Line {e.line}: {e.error}</li>
            ))}
          </ul>
        </div>
      )}

      {rows.length > 0 && (
        <>
          <section>
            <h2>Totals</h2>
            <div className="totals">
              {Object.entries(totals).map(([cat, value]) => (
                <div key={cat} className={"card" + (cat === REVIEW ? " review" : "")}>
                  <div className="cat">{cat}</div>
                  <div className="value">{value}</div>
                  {NOTES[cat] && <div className="muted small">{NOTES[cat]}</div>}
                </div>
              ))}
            </div>
          </section>

          <section>
            <div className="bar">
              <h2>Transactions ({rows.length})</h2>
              <label className="check">
                <input
                  type="checkbox"
                  checked={onlyReview}
                  onChange={(e) => setOnlyReview(e.target.checked)}
                />
                Show only Needs Review ({reviewCount})
              </label>
            </div>

            {visible.length === 0 ? (
              <p className="ok">Nothing left to review.</p>
            ) : (
              <div className="scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th className="num">Amount</th>
                      <th>Category</th>
                      <th>Why</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map((r) => (
                      <tr key={r.id} className={r.needs_review ? "review" : ""}>
                        <td>{r.date}</td>
                        <td>
                          {r.description}
                          {r.possible_duplicate && <span className="tag">possible duplicate</span>}
                        </td>
                        <td className={"num " + (r.amount.startsWith("-") ? "neg" : "pos")}>{r.amount}</td>
                        <td>
                          <select
                            aria-label={"Category for " + r.description}
                            value={r.category}
                            onChange={(e) => changeCategory(r.id, e.target.value)}
                          >
                            {categories.map((c) => (
                              <option key={c} value={c}>{c}</option>
                            ))}
                          </select>
                        </td>
                        <td className="muted small">{r.edited ? "Set by you" : r.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </main>
  );
}
