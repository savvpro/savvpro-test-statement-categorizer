"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "../components/AppShell";
import { fetchStatements, getExportUrl } from "../api";
import { StatementItem } from "../types";
import { DocumentIcon, ExportIcon } from "../components/Icons";

export default function ExportReportsPage() {
  const [statements, setStatements] = useState<StatementItem[]>([]);
  const [selectedStatementId, setSelectedStatementId] = useState<number | null>(null);

  useEffect(() => {
    fetchStatements().then((stmts) => {
      setStatements(stmts);
      if (stmts.length > 0) {
        setSelectedStatementId(stmts[0].id);
      }
    });
  }, []);

  return (
    <AppShell
      pageTitle="Export Tax Reports"
      pageSubtitle="Export categorized statements, Schedule C audit worksheets, and accountant-ready files."
    >
      <div className="card" style={{ padding: "40px 32px", textAlign: "center", maxWidth: 680, margin: "0 auto" }}>
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            background: "#eff6ff",
            color: "#2563eb",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 18px auto",
          }}
        >
          <ExportIcon size={28} />
        </div>

        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>
          Accountant-Ready Schedule C Reports
        </h2>
        <p style={{ fontSize: 13.5, color: "#64748b", lineHeight: 1.5, marginBottom: 28 }}>
          Generate formal audit files matching IRS Form 1040 Schedule C lines. Compatible with TurboTax,
          TaxAct, Drake Software, QuickBooks, and CPA workflows.
        </p>

        {statements.length > 0 ? (
          <div>
            <div className="form-group" style={{ maxWidth: 360, margin: "0 auto 24px auto", textAlign: "left" }}>
              <label className="form-label">Select Statement to Export</label>
              <select
                className="form-select"
                value={selectedStatementId || ""}
                onChange={(e) => setSelectedStatementId(Number(e.target.value))}
              >
                {statements.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.filename} ({s.row_count} rows • {s.account_type})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", justifyContent: "center", gap: 14, flexWrap: "wrap" }}>
              <a
                href={selectedStatementId ? getExportUrl(selectedStatementId, "csv") : "#"}
                download
                className="outline-btn"
                style={{ padding: "10px 22px", fontSize: 14 }}
              >
                <ExportIcon size={16} />
                <span>Download Schedule C (CSV)</span>
              </a>

              <a
                href={selectedStatementId ? getExportUrl(selectedStatementId, "xlsx") : "#"}
                download
                className="top-upload-btn"
                style={{ padding: "10px 22px", fontSize: 14 }}
              >
                <DocumentIcon size={16} />
                <span>Download Excel Workbook (.xlsx)</span>
              </a>
            </div>
          </div>
        ) : (
          <div
            style={{
              padding: "24px",
              background: "#f8fafc",
              border: "1px dashed #cbd5e1",
              borderRadius: 10,
              color: "#64748b",
              fontSize: 13.5,
            }}
          >
            No statements uploaded yet. Upload a statement first to download Schedule C tax reports.
          </div>
        )}
      </div>
    </AppShell>
  );
}
