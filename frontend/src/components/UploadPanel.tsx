import { useId, useRef, useState } from "react";
import {
  ArrowRight,
  FileSpreadsheet,
  Upload,
  Download,
  ShieldCheck,
  X,
  LoaderCircle,
} from "lucide-react";
import type { ImportOptions } from "../types";

interface Props {
  onUpload: (file: File, options: ImportOptions) => void;
  busy: boolean;
  onDemo: () => void;
}

export function UploadPanel({ onUpload, busy, onDemo }: Props) {
  const fileInputId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [options, setOptions] = useState<ImportOptions>({
    date_format: "ISO",
    currency: "USD",
    amount_convention: "negative_expense",
  });
  const input = useRef<HTMLInputElement>(null);
  const select = (candidate?: File) => {
    setError("");
    setFile(null);
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".csv")) {
      setError(
        "Please choose a CSV file. PDF and Excel workbooks are not supported.",
      );
      return;
    }
    if (candidate.size > 5 * 1024 * 1024) {
      setError("This file is too large. Choose a CSV smaller than 5 MB.");
      return;
    }
    if (!candidate.size) {
      setError("This file is empty. Choose a CSV with transactions.");
      return;
    }
    setFile(candidate);
  };
  return (
    <div className="upload-panel">
      <div
        className={`dropzone ${dragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          if (!busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (!busy) select(event.dataTransfer.files[0]);
        }}
      >
        <div className="upload-icon">
          <Upload size={24} strokeWidth={1.6} />
        </div>
        <h3>{file ? file.name : "A fresh start for your statements"}</h3>
        <p>
          {file
            ? `${(file.size / 1024).toFixed(1)} KB · Ready to import`
            : "Drop your CSV here, or choose a file to get started."}
        </p>
        <input
          ref={input}
          className="sr-only"
          id={fileInputId}
          type="file"
          accept=".csv,text/csv"
          aria-label="Choose CSV statement"
          disabled={busy}
          onChange={(event) => {
            select(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
        <div className="button-row centered">
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => input.current?.click()}
          >
            <FileSpreadsheet size={16} />
            {file ? "Choose another file" : "Choose CSV file"}
          </button>
          {file && (
            <button
              className="icon-button"
              aria-label="Remove selected file"
              disabled={busy}
              onClick={() => setFile(null)}
            >
              <X size={18} />
            </button>
          )}
        </div>
        <span className="file-hint">UTF-8 CSV · Up to 5 MB · 10,000 rows</span>
      </div>
      {error && (
        <p className="error-message" role="alert">
          {error}
        </p>
      )}
      {file && (
        <div className="import-options">
          <p className="eyebrow">CHECK YOUR FILE FORMAT</p>
          <div className="form-grid">
            <label>
              Date format
              <select
                value={options.date_format}
                onChange={(e) =>
                  setOptions({ ...options, date_format: e.target.value })
                }
                disabled={busy}
              >
                <option value="ISO">YYYY-MM-DD</option>
                <option value="DMY">DD/MM/YYYY</option>
                <option value="MDY">MM/DD/YYYY</option>
              </select>
            </label>
            <label>
              Currency if missing
              <select
                value={options.currency}
                onChange={(e) =>
                  setOptions({ ...options, currency: e.target.value })
                }
                disabled={busy}
              >
                {["USD", "PKR", "EUR", "GBP", "CAD", "AUD"].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label className="full-width">
              Amount convention
              <select
                value={options.amount_convention}
                onChange={(e) =>
                  setOptions({ ...options, amount_convention: e.target.value })
                }
                disabled={busy}
              >
                <option value="negative_expense">
                  Negative = spending · Positive = money received
                </option>
                <option value="positive_expense">
                  Positive = spending · Negative = money received
                </option>
              </select>
              <span className="field-hint">
                Separate debit/credit columns are detected automatically.
              </span>
            </label>
          </div>
          <button
            className="button primary full-button"
            disabled={busy}
            onClick={() => onUpload(file, options)}
          >
            {busy ? (
              <LoaderCircle className="spin" size={17} />
            ) : (
              <ArrowRight size={17} />
            )}
            {busy ? "Reading your statement…" : "Import statement"}
          </button>
        </div>
      )}
      <div className="sample-row">
        <span>Just taking a look?</span>
        <button className="text-button" disabled={busy} onClick={onDemo}>
          Try sample data <ArrowRight size={14} />
        </button>
      </div>
      <div className="upload-footer">
        <span>
          <ShieldCheck size={15} /> Stored on this computer
        </span>
        <a href="/api/samples/freelancer_statement.csv" download>
          <Download size={14} /> Sample CSV
        </a>
      </div>
      <p className="subtle-note">
        Use fictional statements for this assessment. No bank connection or API
        key needed.
      </p>
    </div>
  );
}
