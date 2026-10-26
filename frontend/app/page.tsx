"use client";
import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Txn = {
  id: number; date: string; description: string; amount: number; kind: string;
  category: string; confidence: number; needs_review: boolean; reason: string;
};
type Statement = {
  id: string; filename: string; transactions: Txn[]; warnings: string[];
  summary: { category_totals: Record<string, number>; income_total: number; excluded_total: number; needs_review_count: number };
};

const money = (n: number) => n.toLocaleString("en-US", { style: "currency", currency: "USD" });

export default function Home() {
  const [stmt, setStmt] = useState<Statement | null>(null);
  const [cats, setCats] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [onlyReview, setOnlyReview] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch(`${API}/categories`).then((r) => r.json()).then(setCats).catch(() => setError("Cannot reach the backend."));
  }, []);

  async function call(url: string, init: RequestInit) {
    setBusy(true); setError("");
    try {
      const res = await fetch(url, init);
      const body = await res.json();
      if (!res.ok) throw new Error(body.detail ?? "Request failed");
      setStmt(body);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally { setBusy(false); }
  }

  const upload = (file?: File) => {
    if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    call(`${API}/statements`, { method: "POST", body: fd });
  };

  const fix = (t: Txn, category: string) =>
    stmt && call(`${API}/statements/${stmt.id}/transactions/${t.id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category, remember: true }),
    });

  const rows = stmt?.transactions.filter((t) => !onlyReview || t.needs_review) ?? [];
  const th = { textAlign: "left" as const, padding: 8, borderBottom: "2px solid #ddd" };
  const td = { padding: 8, borderBottom: "1px solid #eee", verticalAlign: "top" as const };

  return (
    <main style={{ maxWidth: 1000, margin: "0 auto", padding: 24 }}>
      <h1>Statement Categorizer</h1>
      <p>Upload a CSV bank or credit card statement. Rows the app is not sure about go to <b>Needs Review</b>.</p>
      <input type="file" accept=".csv" disabled={busy} onChange={(e) => upload(e.target.files?.[0])} />
      {error && <p role="alert" style={{ color: "#b00020" }}>{error}</p>}

      {stmt && (
        <>
          {stmt.warnings.map((w, i) => <p key={i} style={{ color: "#8a5a00" }}>⚠ {w}</p>)}
          <h2>Totals</h2>
          <table style={{ borderCollapse: "collapse" }}>
            <tbody>
              {Object.entries(stmt.summary.category_totals).map(([c, v]) => (
                <tr key={c}><td style={td}>{c}</td><td style={{ ...td, textAlign: "right" }}>{money(v)}</td></tr>
              ))}
              <tr><td style={td}><i>Income (not spending)</i></td><td style={{ ...td, textAlign: "right" }}>{money(stmt.summary.income_total)}</td></tr>
              <tr><td style={td}><i>Transfers and card payments (excluded)</i></td><td style={{ ...td, textAlign: "right" }}>{money(stmt.summary.excluded_total)}</td></tr>
            </tbody>
          </table>

          <h2>Transactions</h2>
          <label>
            <input type="checkbox" checked={onlyReview} onChange={(e) => setOnlyReview(e.target.checked)} />{" "}
            Show only Needs Review ({stmt.summary.needs_review_count})
          </label>
          <table style={{ borderCollapse: "collapse", width: "100%", marginTop: 12, background: "#fff" }}>
            <thead><tr>{["Date", "Description", "Amount", "Category", "Why"].map((h) => <th key={h} style={th}>{h}</th>)}</tr></thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id} style={{ background: t.needs_review ? "#fff6e0" : undefined }}>
                  <td style={td}>{t.date}</td>
                  <td style={td}>{t.description}</td>
                  <td style={{ ...td, textAlign: "right" }}>{money(t.amount)}</td>
                  <td style={td}>
                    <select value={t.category} disabled={busy} onChange={(e) => fix(t, e.target.value)} aria-label={`Category for ${t.description}`}>
                      {cats.filter((c) => c !== "Needs Review" || t.category === "Needs Review").map((c) => <option key={c}>{c}</option>)}
                    </select>
                  </td>
                  <td style={{ ...td, fontSize: 13, color: "#555" }}>{t.reason} ({Math.round(t.confidence * 100)}%)</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </main>
  );
}
