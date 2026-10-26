"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import { fetchStatements, fetchSummary, getExportUrl } from "../api";
import { CategoryTotal, StatementItem, SummaryData } from "../types";
import { DocumentIcon, ExportIcon, ShieldCheckIcon } from "../components/Icons";

export default function CategoriesPage() {
  const [statements, setStatements] = useState<StatementItem[]>([]);
  const [activeStatementId, setActiveStatementId] = useState<number | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);

  const loadData = async (statementId?: number) => {
    try {
      let stmts = statements;
      if (stmts.length === 0) {
        stmts = await fetchStatements();
        setStatements(stmts);
      }
      const sId = statementId || activeStatementId || (stmts.length > 0 ? stmts[0].id : null);
      if (sId) {
        setActiveStatementId(sId);
        const sum = await fetchSummary(sId);
        if (sum) setSummary(sum);
      }
    } catch (err) {
      console.error("Error loading categories:", err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totals: CategoryTotal[] = summary?.totals || [];

  return (
    <AppShell
      pageTitle="Schedule C Categories"
      pageSubtitle="Audit IRS Schedule C expense categories, deductibility percentages, and compliant tax lines."
      onStatementUploaded={() => loadData()}
    >
      {/* Top Banner & Statement Selector */}
      <div className="card" style={{ padding: "20px 24px", marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#0f172a" }}>
              IRS Form 1040 Schedule C Breakdown
            </div>
            <div style={{ fontSize: 13, color: "#64748b", marginTop: 2 }}>
              Tax Year 2026 • Sole Proprietor / Single-Member LLC
            </div>
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            {statements.length > 1 && (
              <select
                className="form-select"
                style={{ width: "auto" }}
                value={activeStatementId || ""}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  setActiveStatementId(id);
                  loadData(id);
                }}
              >
                {statements.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.filename}
                  </option>
                ))}
              </select>
            )}

            {activeStatementId && (
              <>
                <a
                  href={getExportUrl(activeStatementId, "csv")}
                  download
                  className="outline-btn"
                >
                  <ExportIcon size={14} />
                  <span>Download CSV</span>
                </a>
                <a
                  href={getExportUrl(activeStatementId, "xlsx")}
                  download
                  className="top-upload-btn"
                >
                  <DocumentIcon size={14} />
                  <span>Download Excel</span>
                </a>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Categories Table */}
      <div className="card" style={{ padding: "0 0 20px 0", marginBottom: 20 }}>
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Schedule C Line</th>
                <th>Category Name</th>
                <th>Classification</th>
                <th>Deductible %</th>
                <th>Transactions</th>
                <th style={{ textAlign: "right" }}>Total Amount</th>
                <th style={{ textAlign: "right" }}>Tax Deductible</th>
              </tr>
            </thead>
            <tbody>
              {totals.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
                    <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 4 }}>No category totals yet</div>
                    <div style={{ fontSize: 12 }}>Upload a bank or credit card statement to generate the category breakdown.</div>
                  </td>
                </tr>
              ) : (
                totals.map((cat) => {
                  const totalDollars = `$${(Math.abs(cat.total_cents) / 100).toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}`;
                  const deductibleDollars = `$${(Math.abs(cat.deductible_cents) / 100).toLocaleString("en-US", {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}`;

                  return (
                    <tr key={cat.category}>
                      <td style={{ fontWeight: 600, color: "#2563eb" }}>
                        {cat.schedule_c_line}
                      </td>
                      <td style={{ fontWeight: 600, color: "#0f172a" }}>
                        {cat.label}
                      </td>
                      <td>
                        <span
                          className={`status-pill ${
                            cat.cat_type === "income"
                              ? "categorized"
                              : cat.cat_type === "review"
                              ? "needs_review"
                              : cat.cat_type === "excluded"
                              ? "excluded"
                              : "categorized"
                          }`}
                        >
                          {cat.cat_type.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span
                          style={{
                            fontWeight: 600,
                            color: cat.deductible_pct === 50 ? "#d97706" : "#0f172a",
                          }}
                        >
                          {cat.deductible_pct}%
                          {cat.deductible_pct === 50 && " (50% Meal Rule)"}
                        </span>
                      </td>
                      <td style={{ color: "#64748b" }}>{cat.count} row(s)</td>
                      <td
                        style={{
                          textAlign: "right",
                          fontWeight: 600,
                          color: cat.cat_type === "income" ? "#16a34a" : "#0f172a",
                        }}
                      >
                        {cat.cat_type === "income" ? `+${totalDollars}` : `-${totalDollars}`}
                      </td>
                      <td
                        style={{
                          textAlign: "right",
                          fontWeight: 700,
                          color: cat.deductible_cents !== 0 ? "#2563eb" : "#94a3b8",
                        }}
                      >
                        {cat.deductible_cents !== 0 ? deductibleDollars : "$0.00"}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* IRS Compliance Info */}
      <div className="compliance-box">
        <div className="compliance-icon">
          <ShieldCheckIcon size={22} />
        </div>
        <div className="compliance-content">
          <span className="compliance-title">IRS Tax Code Rule Compliance</span>
          <p className="compliance-desc">
            TaxSort automatically computes 50% allowable deduction limits for qualifying business meals
            under IRC § 274(n), strips non-deductible personal withdrawals and owner transfers, and aggregates
            Schedule C Line 8 (Advertising), Line 18 (Office/Software), and Line 24a (Travel) according to official IRS standards.
          </p>
        </div>
      </div>
    </AppShell>
  );
}
