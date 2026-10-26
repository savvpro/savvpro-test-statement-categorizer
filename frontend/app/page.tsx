"use client";
import { useState, useMemo } from "react";
import { uploadStatement, updateCategory, Row } from "../lib/api";

const CATEGORIES = [
  "Refund", "Not Spending", "Income/Payout", "Platform Fees",
  "Shipping", "Inventory/Supplies", "Marketing", "Software", "Needs Review",
];

export default function Home() {
  const [rows, setRows] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  // Filter state
  const [showOnlyReview, setShowOnlyReview] = useState(false);

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    
    setFileName(f.name);
    setBusy(true);
    setError(null);
    
    try {
      const data = await uploadStatement(f);
      setRows(data);
      setShowOnlyReview(false); // Reset filter on new upload
    } catch (err: any) {
      setError(err.message || "Failed to process file.");
      setRows([]);
    } finally {
      setBusy(false);
    }
  }

  async function onFix(id: string, category: string) {
    // Optimistically update UI, then sync with backend
    const updated = await updateCategory(id, category);
    setRows((prev) => prev.map((r) => (r.id === id ? updated : r)));
  }

  // Calculate totals based on CURRENT state (updates when dropdown changes)
  const totals = useMemo(() => {
    return rows.reduce<Record<string, number>>((acc, r) => {
      if (r.category === "Not Spending" || r.category === "Refund") return acc;
      acc[r.category] = (acc[r.category] || 0) + parseFloat(r.amount);
      return acc;
    }, {});
  }, [rows]);

  // Count how many need review
  const reviewCount = rows.filter((r) => r.category === "Needs Review").length;

  // Filter rows for the table display
  const displayedRows = showOnlyReview 
    ? rows.filter((r) => r.category === "Needs Review") 
    : rows;

  // Export to CSV feature
  function exportCSV() {
    const headers = ["Date", "Description", "Amount", "Category", "Confidence", "Reason"];
    const csvContent = [
      headers.join(","),
      ...rows.map(r => `"${r.date}","${r.description}",${r.amount},"${r.category}",${r.confidence},"${r.reason}"`)
    ].join("\n");

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `categorized_${fileName || "statement"}`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  return (
    <div className="container">
      <header>
        <h1>Statement Categorizer</h1>
        <p className="subtitle">Upload your CSV to automatically categorize transactions.</p>
      </header>

      {/* Upload Area */}
      <div className="upload-card">
        {busy ? (
          <p style={{ color: "var(--primary)", fontWeight: "600" }}>Reading file and running brain...</p>
        ) : rows.length > 0 ? (
          <div>
            <p style={{ color: "var(--success-text)", fontWeight: "bold", marginBottom: "10px" }}>
              ✓ Successfully processed: {fileName}
            </p>
            <label style={{ cursor: "pointer", color: "var(--text-muted)", textDecoration: "underline" }}>
              Upload a different file
              <input type="file" accept=".csv" onChange={onFile} style={{ display: "none" }} />
            </label>
          </div>
        ) : (
          <input type="file" accept=".csv" onChange={onFile} />
        )}
        {error && <p style={{ color: "var(--danger-text)", marginTop: "10px" }}>Error: {error}</p>}
      </div>

      {rows.length > 0 && (
        <>
          {/* Action Bar */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div style={{ display: "flex", gap: "15px", alignItems: "center" }}>
              <span style={{ 
                background: reviewCount > 0 ? "var(--warning-bg)" : "var(--success-bg)",
                color: reviewCount > 0 ? "var(--warning-text)" : "var(--success-text)",
                padding: "6px 12px", borderRadius: "8px", fontSize: "0.9rem", fontWeight: 600
              }}>
                {reviewCount} transaction{reviewCount !== 1 ? 's' : ''} need review
              </span>
              
              <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer", fontSize: "0.9rem" }}>
                <input 
                  type="checkbox" 
                  checked={showOnlyReview} 
                  onChange={(e) => setShowOnlyReview(e.target.checked)} 
                />
                Show only Needs Review
              </label>
            </div>

            <button onClick={exportCSV} style={{
              background: "var(--surface)", color: "var(--text)", border: "1px solid var(--border)",
              padding: "8px 16px", borderRadius: "8px", cursor: "pointer", fontWeight: 500
            }}>
              Export Corrected CSV
            </button>
          </div>

          {/* Table */}
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Description</th>
                  <th style={{ textAlign: "right" }}>Amount</th>
                  <th>Category</th>
                  <th>Confidence</th>
                  <th>Brain Reason</th>
                </tr>
              </thead>
              <tbody>
                {displayedRows.map((r) => {
                  const isReview = r.category === "Needs Review";
                  const amount = parseFloat(r.amount);
                  const isExpense = amount < 0;
                  
                  return (
                    <tr key={r.id} className={isReview ? "needs-review" : ""}>
                      <td style={{ whiteSpace: "nowrap", color: "var(--text-muted)" }}>{r.date}</td>
                      <td style={{ fontWeight: 500 }}>{r.description}</td>
                      <td style={{ textAlign: "right", fontWeight: 600, color: isExpense ? "var(--danger-text)" : "var(--success-text)" }}>
                        {isExpense ? "-" : "+"}${Math.abs(amount).toFixed(2)}
                      </td>
                      <td>
                        <select
                          value={r.category}
                          onChange={(e) => onFix(r.id, e.target.value)}
                          style={{ fontWeight: isReview ? "600" : "400", borderColor: isReview ? "var(--warning-text)" : "var(--border)" }}
                        >
                          {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </td>
                      <td>
                        <span className={`badge ${r.confidence >= 0.8 ? "badge-high" : "badge-low"}`}>
                          {(r.confidence * 100).toFixed(0)}%
                        </span>
                      </td>
                      <td style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>{r.reason}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {displayedRows.length === 0 && (
              <p style={{ padding: "2rem", textAlign: "center", color: "var(--text-muted)" }}>
                No transactions to show.
              </p>
            )}
          </div>

          {/* Totals */}
          <div className="totals-section">
            <h2>Totals by Category</h2>
            <div className="totals-grid">
              {Object.entries(totals).map(([category, amount]) => (
                <div key={category} className="total-card">
                  <h3>{category}</h3>
                  <p>${Math.abs(amount).toFixed(2)}</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}