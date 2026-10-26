import { useEffect, useMemo, useState } from "react";
import { getCategories, loadSample, saveCategory, uploadStatement } from "./api";

const FILTERS = [
  ["all", "All"],
  ["review", "Needs review"],
  ["expense", "Expenses"],
  ["income", "Income"],
  ["excluded", "Set aside"],
  ["personal", "Personal"],
];

const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

function money(value) {
  const formatted = usd.format(Math.abs(Number(value) || 0));
  return Number(value) < 0 ? `−${formatted}` : formatted;
}

function formatDate(iso) {
  if (!iso) return "—";
  const [year, month, day] = iso.split("-").map(Number);
  const names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${names[month - 1]} ${day}, ${year}`;
}

function categoryName(transaction) {
  if (transaction.category === "refund" && transaction.offsets_label) {
    return `Refund · ${transaction.offsets_label}`;
  }
  return transaction.category_label;
}

function draftFor(transaction) {
  let category = transaction.category;
  if (transaction.needs_review) {
    category = transaction.suggestion || "";
  } else if (transaction.category === "refund" && transaction.offsets_category) {
    category = transaction.offsets_category;
  }
  return { category, remember: Boolean(transaction.remember_safe) };
}

function matchesFilter(transaction, filter, query) {
  const haystack = `${transaction.description} ${transaction.category_label} ${transaction.suggestion_label || ""}`.toLowerCase();
  if (query && !haystack.includes(query.trim().toLowerCase())) return false;
  if (filter === "review") return transaction.needs_review;
  if (filter === "expense") return transaction.bucket === "expense" || transaction.bucket === "refund";
  if (filter === "income") return transaction.bucket === "income";
  if (filter === "excluded") return transaction.bucket === "excluded";
  if (filter === "personal") return transaction.bucket === "personal";
  return true;
}

function exportCsv(statement) {
  const header = ["date", "description", "amount", "category", "needs_review", "confidence", "reason", "offsets_category"];
  const lines = [header.join(",")];
  for (const transaction of statement.transactions) {
    const cells = [
      transaction.date || "",
      transaction.description,
      transaction.amount,
      transaction.category,
      transaction.needs_review,
      transaction.confidence,
      transaction.reason,
      transaction.offsets_category || "",
    ].map((value) => `"${String(value).replaceAll('"', '""')}"`);
    lines.push(cells.join(","));
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "proofsheet-categorized.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export default function App() {
  const [categories, setCategories] = useState([]);
  const [accountType, setAccountType] = useState("credit_card");
  const [statement, setStatement] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [savingId, setSavingId] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getCategories().then(setCategories).catch(() => {
      setError("The API is not running. Start the backend on port 8000, then refresh.");
    });
  }, []);

  function adopt(next) {
    setStatement(next);
    setDrafts(Object.fromEntries(next.transactions.map((transaction) => [transaction.id, draftFor(transaction)])));
    setError("");
  }

  async function onUpload(file) {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      adopt(await uploadStatement(file, accountType));
      setFilter("all");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onSample() {
    setBusy(true);
    setError("");
    setAccountType("credit_card");
    try {
      adopt(await loadSample());
      setFilter("review");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function onSave(transaction) {
    const draft = drafts[transaction.id];
    if (!draft?.category) {
      setError("Choose a category before saving.");
      return;
    }
    setSavingId(transaction.id);
    setError("");
    try {
      adopt(await saveCategory(statement.id, transaction.id, draft.category, draft.remember));
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingId("");
    }
  }

  const visible = useMemo(() => {
    if (!statement) return [];
    return statement.transactions.filter((transaction) => matchesFilter(transaction, filter, query));
  }, [statement, filter, query]);

  const maxCategory = statement
    ? Math.max(1, ...statement.summary.categories.map((item) => Math.abs(item.total)))
    : 1;

  return (
    <div className="page">
      <header className="top">
        <div>
          <p className="eyebrow">Freelance designer · tax time</p>
          <h1>Proofsheet</h1>
          <p className="lede">
            Upload a business credit-card statement. Each charge is filed only when a rule is sure.
            Unsure rows stay out of the deductible total until you confirm them.
          </p>
        </div>
        <div className="upload-card">
          <fieldset>
            <legend>How this file records direction</legend>
            <label>
              <input
                type="radio"
                name="account"
                checked={accountType === "credit_card"}
                onChange={() => setAccountType("credit_card")}
              />
              Credit card, charges positive
            </label>
            <label>
              <input
                type="radio"
                name="account"
                checked={accountType === "bank"}
                onChange={() => setAccountType("bank")}
              />
              Bank account, deposits positive
            </label>
          </fieldset>
          <label className="drop">
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={(event) => {
                const file = event.target.files?.[0];
                event.target.value = "";
                onUpload(file);
              }}
            />
            <span>{busy ? "Reading…" : "Upload CSV"}</span>
            <small>Date, description, and amount. Debit and credit columns work too.</small>
          </label>
          <button type="button" className="secondary" onClick={onSample} disabled={busy}>
            Load the Studio North sample
          </button>
        </div>
      </header>

      {error ? <p className="banner">{error}</p> : null}

      {!statement ? (
        <section className="empty">
          <h2>A January statement is ready to try</h2>
          <p>
            Studio North is fictional. The sample includes software, travel, a refund, a card payment,
            a transfer, a duplicate charge, and merchants the rules refuse to guess.
          </p>
        </section>
      ) : (
        <>
          <section className="stats" aria-label="Totals">
            <article>
              <span>Deductible expenses</span>
              <strong data-testid="deductible-total">{money(statement.summary.deductible_total)}</strong>
              <small>Reviewed expenses, after refunds</small>
            </article>
            <article className="review-stat">
              <span>Still to review</span>
              <strong data-testid="review-count">
                {statement.summary.needs_review_count}
                <em> rows</em>
              </strong>
              <small>{money(statement.summary.needs_review_total)} held out</small>
            </article>
            <article>
              <span>Client income</span>
              <strong>{money(statement.summary.income_total)}</strong>
              <small>Payouts, not expenses</small>
            </article>
            <article>
              <span>Set aside</span>
              <strong>{money(statement.summary.excluded_total)}</strong>
              <small>Card payments and transfers</small>
            </article>
          </section>

          <section className="split">
            <div>
              <h2>By category</h2>
              {statement.summary.categories.length === 0 ? (
                <p className="muted">No filed expenses yet.</p>
              ) : (
                <ul className="bars">
                  {statement.summary.categories.map((item) => (
                    <li key={item.id}>
                      <div>
                        <span>{item.label}</span>
                        <b>{money(item.total)}</b>
                      </div>
                      <i style={{ width: `${(Math.abs(item.total) / maxCategory) * 100}%` }} />
                    </li>
                  ))}
                </ul>
              )}
              {statement.summary.personal_total ? (
                <p className="muted">Personal charges held out: {money(statement.summary.personal_total)}</p>
              ) : null}
              {statement.summary.unassigned_refunds ? (
                <p className="muted">
                  Refunds still waiting for a category: {money(statement.summary.unassigned_refunds)}
                </p>
              ) : null}
            </div>
            <div>
              <h2>File notes</h2>
              <p className="file-name">{statement.filename}</p>
              {statement.warnings.length === 0 ? (
                <p className="muted">Every row had a readable date and amount.</p>
              ) : (
                <ul className="warnings">
                  {statement.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="ledger">
            <div className="toolbar">
              <div className="filters" role="tablist">
                {FILTERS.map(([id, name]) => (
                  <button
                    key={id}
                    type="button"
                    className={filter === id ? "on" : ""}
                    onClick={() => setFilter(id)}
                  >
                    {name}
                    {id === "review" ? ` (${statement.summary.needs_review_count})` : ""}
                  </button>
                ))}
              </div>
              <input
                type="search"
                placeholder="Search description"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                aria-label="Search transactions"
              />
              <button type="button" className="secondary" onClick={() => exportCsv(statement)}>
                Export CSV
              </button>
            </div>

            <div className="table-wrap">
              <table data-testid="transaction-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Transaction</th>
                    <th>Amount</th>
                    <th>Category</th>
                  </tr>
                </thead>
                <tbody>
                  {visible.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="muted">
                        Nothing in this view.
                      </td>
                    </tr>
                  ) : (
                    visible.map((transaction) => {
                      const draft = drafts[transaction.id] || draftFor(transaction);
                      return (
                        <tr key={transaction.id} className={transaction.needs_review ? "needs-review" : ""}>
                          <td className="date">{formatDate(transaction.date)}</td>
                          <td>
                            <div className="desc">{transaction.description || "No description"}</div>
                            <div className="reason">{transaction.reason}</div>
                            <div className="chips">
                              {transaction.pending ? <span>Pending</span> : null}
                              {transaction.duplicate ? <span>Possible duplicate</span> : null}
                              {transaction.needs_review && transaction.suggestion_label ? (
                                <span>Suggestion: {transaction.suggestion_label}</span>
                              ) : null}
                            </div>
                          </td>
                          <td className={transaction.amount < 0 ? "in" : "out"}>{money(transaction.amount)}</td>
                          <td>
                            <div className={`badge ${transaction.bucket}`}>{categoryName(transaction)}</div>
                            <div className="confidence">
                              {transaction.needs_review ? "Needs you" : `${Math.round(transaction.confidence * 100)}% match`}
                            </div>
                            <div className="editor">
                              <label className="sr" htmlFor={`cat-${transaction.id}`}>
                                Category for {transaction.description || "this row"}
                              </label>
                              <select
                                id={`cat-${transaction.id}`}
                                data-testid={`category-${transaction.id}`}
                                value={draft.category}
                                onChange={(event) =>
                                  setDrafts((current) => ({
                                    ...current,
                                    [transaction.id]: { ...draft, category: event.target.value },
                                  }))
                                }
                              >
                                <option value="">Choose</option>
                                {categories.map((category) => (
                                  <option key={category.id} value={category.id}>
                                    {category.label}
                                  </option>
                                ))}
                              </select>
                              <label className="remember">
                                <input
                                  type="checkbox"
                                  checked={draft.remember}
                                  onChange={(event) =>
                                    setDrafts((current) => ({
                                      ...current,
                                      [transaction.id]: { ...draft, remember: event.target.checked },
                                    }))
                                  }
                                />
                                Remember merchant
                              </label>
                              <button
                                type="button"
                                data-testid={`save-${transaction.id}`}
                                onClick={() => onSave(transaction)}
                                disabled={savingId === transaction.id}
                              >
                                {savingId === transaction.id ? "Saving…" : "Save"}
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
