"use client";

import React from "react";
import { AppShell } from "../components/AppShell";
import { useAuth } from "../context/AuthContext";

export default function SettingsPage() {
  const { user, logout } = useAuth();

  return (
    <AppShell
      pageTitle="Workspace Settings"
      pageSubtitle="Configure your account, categorization preferences, and deterministic engine rules."
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 800 }}>
        {/* Account Profile Card */}
        <div className="card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 16 }}>
            Account Profile
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
            <div>
              <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Full Name</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#0f172a" }}>
                {user?.full_name || "Tax Filer"}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 12, color: "#64748b", marginBottom: 4 }}>Email Address</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: "#0f172a" }}>
                {user?.email || "Personal Account"}
              </div>
            </div>
          </div>
          <button
            className="outline-btn"
            style={{ color: "#ef4444", borderColor: "#fca5a5" }}
            onClick={logout}
          >
            Sign Out of TaxSort
          </button>
        </div>

        {/* Engine Configuration Card */}
        <div className="card" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, color: "#0f172a", marginBottom: 16 }}>
            Deterministic Categorization Brain
          </h2>
          <p style={{ fontSize: 13, color: "#64748b", lineHeight: 1.5, marginBottom: 16 }}>
            TaxSort uses pure deterministic code (normalization, exclusions, transfer netting,
            curated merchant dictionaries, and user override rules). No non-deterministic LLM is in the tax classification path.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <div style={{ padding: 12, background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: 11, color: "#64748b" }}>Curated Merchants</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", marginTop: 2 }}>~300</div>
            </div>
            <div style={{ padding: 12, background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: 11, color: "#64748b" }}>Fuzzy Match Cap</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", marginTop: 2 }}>85%</div>
            </div>
            <div style={{ padding: 12, background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: 11, color: "#64748b" }}>Backend Status</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#16a34a", marginTop: 4 }}>Connected (8000)</div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
