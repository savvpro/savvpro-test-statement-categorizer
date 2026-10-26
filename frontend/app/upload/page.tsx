"use client";

import React, { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "../components/AppShell";
import { uploadStatement } from "../api";
import { UploadCloudIcon } from "../components/Icons";

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [accountType, setAccountType] = useState<"credit_card" | "checking">("credit_card");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      await uploadStatement(file, accountType);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to parse statement.");
    } finally {
      setLoading(false);
    }
  };

  // Helper to test with bundled sample files
  const handleLoadSample = async (sampleName: string, type: "credit_card" | "checking") => {
    setLoading(true);
    setError(null);
    try {
      const sampleCsv =
        sampleName === "freelancer_amex.csv"
          ? `Date,Description,Amount\n01/04/2026,ADOBE CREATIVE CLOUD,-59.99\n01/05/2026,PAYMENT THANK YOU - AUTOPAY,1500.00\n01/07/2026,SQ *JOES CAFE 9921,-14.20\n01/09/2026,AMZN MKTP US 3K1F2,-131.07\n01/10/2026,GOOGLE ADS 4829102,-250.00\n01/12/2026,DELTA AIR LINES 00628192,-412.50\n01/14/2026,STRIPE PAYOUT,3200.00\n01/15/2026,ONLINE PAYMENT - THANK YOU,-1000.00\n01/16/2026,FIGMA MONTHLY,-15.00\n01/18/2026,GITHUB,-10.00\n01/20/2026,UBER TRIP 01/20,-28.40\n01/22/2026,APPLE.COM/BILL,-2.99\n01/24/2026,TST* BLUE BOTTLE COFFEE,-6.75\n01/25/2026,USPS PO 381920,-18.40\n01/26/2026,REFUND - DELTA AIR LINES,45.00\n01/28/2026,STAPLES #1283,-87.32\n01/29/2026,WEWORK ALL ACCESS,-350.00\n01/30/2026,ZOOM.US SUBSCRIPTION,-15.99\n01/31/2026,AMAZON.COM*2C9D0,-42.80\n02/02/2026,LYFT *RIDE 02/02,-18.20\n02/05/2026,OFFICE DEPOT #847,-111.07\n`
          : `Transaction Date,Details,Debit,Credit\n01/04/2026,DIRECT DEPOSIT ACME LLC,,4500.00\n01/06/2026,ONLINE TRANSFER TO SAVINGS,1000.00,\n01/08/2026,CHECKCARD 0108 STAPLES #1234,45.67,\n01/10/2026,DEBIT CARD PURCHASE POS WEWORK MEMBERSHIP,350.00,\n01/12/2026,ACH DEBIT GEICO AUTO INS,142.50,\n01/15/2026,WIRE TRANSFER OUT,2000.00,\n01/18/2026,ZELLE PAYMENT FROM CLIENT,,800.00\n01/20/2026,POS CHIPOTLE MEXICAN GRI 1234,12.50,\n01/22/2026,ATM CASH WITHDRAWAL,100.00,\n01/25/2026,MONTHLY SERVICE FEE,15.00,\n01/28/2026,ACH DEPOSIT STRIPE TRANSFER,,1650.00\n01/30/2026,AUTOPAY AMEX GOLD,1200.00,\n`;

      const blob = new Blob([sampleCsv], { type: "text/csv" });
      const sampleFile = new File([blob], sampleName, { type: "text/csv" });
      await uploadStatement(sampleFile, type);
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load sample statement.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell
      pageTitle="Upload Statement"
      pageSubtitle="Upload bank or credit card statements (CSV or PDF) for deterministic Schedule C tax categorization."
    >
      <div className="card" style={{ padding: "36px 32px", maxWidth: 640, margin: "0 auto" }}>
        {error && (
          <div
            style={{
              padding: "12px 16px",
              background: "#fef2f2",
              border: "1px solid #fecaca",
              color: "#b91c1c",
              borderRadius: 8,
              fontSize: 13,
              marginBottom: 20,
            }}
          >
            {error}
          </div>
        )}

        {/* Dropzone */}
        <div
          className={`dropzone ${isDragging ? "active" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{ padding: "48px 24px" }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.pdf"
            style={{ display: "none" }}
            onChange={(e) => {
              if (e.target.files?.[0]) setFile(e.target.files[0]);
            }}
          />
          <div className="dropzone-icon">
            <UploadCloudIcon size={44} />
          </div>
          <div className="dropzone-title" style={{ fontSize: 16 }}>
            {file ? file.name : "Choose a statement file or drag & drop here"}
          </div>
          <div className="dropzone-hint" style={{ fontSize: 13, marginTop: 4 }}>
            Accepts CSV, TSV, or PDF bank / credit card export statements
          </div>
        </div>

        {/* Account Type */}
        <div className="form-group" style={{ marginBottom: 24 }}>
          <label className="form-label">Account Classification</label>
          <select
            className="form-select"
            value={accountType}
            onChange={(e) => setAccountType(e.target.value as "credit_card" | "checking")}
          >
            <option value="credit_card">Credit Card Statement (American Express, Chase, Capital One, Citi)</option>
            <option value="checking">Checking / Bank Account (Mercury, Chase, Wells Fargo, Relay)</option>
          </select>
        </div>

        <button
          className="btn-primary"
          style={{ width: "100%", padding: "12px", fontSize: 14 }}
          onClick={handleUpload}
          disabled={!file || loading}
        >
          {loading ? "Processing & Categorizing Statement..." : "Categorize Statement"}
        </button>

        {/* Sample Loaders */}
        <div style={{ marginTop: 28, paddingTop: 20, borderTop: "1px solid #f1f5f9", textAlign: "center" }}>
          <div style={{ fontSize: 12, color: "#64748b", marginBottom: 12 }}>
            Or test with a bundled sample freelancer statement:
          </div>
          <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
            <button
              className="outline-btn"
              onClick={() => handleLoadSample("freelancer_amex.csv", "credit_card")}
              disabled={loading}
            >
              Load Amex Credit Card (21 rows)
            </button>
            <button
              className="outline-btn"
              onClick={() => handleLoadSample("freelancer_checking.csv", "checking")}
              disabled={loading}
            >
              Load Checking Account (12 rows)
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
