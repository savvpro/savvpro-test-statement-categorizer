"use client";

import React, { useRef, useState } from "react";
import { CloseIcon, UploadCloudIcon } from "./Icons";
import { uploadStatement } from "../api";

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (data?: unknown) => void;
}

export function UploadModal({ isOpen, onClose, onSuccess }: UploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [accountType, setAccountType] = useState<"credit_card" | "checking">(
    "credit_card"
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

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
      const res = await uploadStatement(file, accountType);
      onSuccess(res);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to parse and categorize statement.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">Upload Statement</div>
          <button className="modal-close-btn" onClick={onClose}>
            <CloseIcon size={18} />
          </button>
        </div>

        {error && (
          <div
            style={{
              padding: "10px 14px",
              background: "#fef2f2",
              border: "1px solid #fecaca",
              color: "#b91c1c",
              borderRadius: 8,
              fontSize: 13,
              marginBottom: 16,
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
            <UploadCloudIcon size={36} />
          </div>
          <div className="dropzone-title">
            {file ? file.name : "Click to browse or drag & drop statement"}
          </div>
          <div className="dropzone-hint">
            Supports CSV and PDF bank/credit-card statements
          </div>
        </div>

        {/* Account Type Selector */}
        <div className="form-group">
          <label className="form-label">Account Type</label>
          <select
            className="form-select"
            value={accountType}
            onChange={(e) =>
              setAccountType(e.target.value as "credit_card" | "checking")
            }
          >
            <option value="credit_card">Credit Card Statement</option>
            <option value="checking">Checking / Bank Account Statement</option>
          </select>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={handleUpload}
            disabled={!file || loading}
          >
            {loading ? "Categorizing Transactions..." : "Categorize Statement"}
          </button>
        </div>
      </div>
    </div>
  );
}
