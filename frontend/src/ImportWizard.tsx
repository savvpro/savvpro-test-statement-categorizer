import { useState, type FormEvent } from "react";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  FileSpreadsheet,
  Info,
  LoaderCircle,
  ShieldCheck,
  Upload,
} from "lucide-react";
import { api, ApiError } from "./api";
import type { ImportOptions, Preview, Statement } from "./types";
import { ErrorNotice } from "./components";

type Props = {
  onImported: (statement: Statement, existing: boolean) => Promise<void>;
  onCancel: () => void;
};
export default function ImportWizard({ onImported, onCancel }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [options, setOptions] = useState<ImportOptions>({
    date_column: "",
    description_column: "",
    amount_column: "",
    debit_column: "",
    credit_column: "",
    mode: "signed",
    date_format: "iso",
    sign_convention: "negative_outgoing",
    currency: "USD",
  });
  const update = (field: keyof ImportOptions, value: string) => {
    setOptions((v) => ({ ...v, [field]: value }));
    setConfirmed(false);
  };
  async function inspect(selected: File) {
    setError(null);
    setBusy(true);
    setPreview(null);
    setConfirmed(false);
    try {
      if (selected.size > 2 * 1024 * 1024)
        throw new ApiError(
          "This file is larger than 2 MiB. Split it into smaller statements.",
        );
      setFile(selected);
      const data = new FormData();
      data.append("file", selected);
      const result = await api<Preview>("/imports/preview", {
        method: "POST",
        body: data,
      });
      setPreview(result);
      setOptions((v) => ({
        ...v,
        ...result.suggestions,
        mode:
          result.suggestions.debit_column &&
          result.suggestions.credit_column &&
          !result.suggestions.amount_column
            ? "split"
            : "signed",
      }));
    } catch (e) {
      setError(
        e instanceof ApiError ? e : new ApiError("Could not read this file."),
      );
    } finally {
      setBusy(false);
    }
  }
  async function sample() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/demo");
      if (!response.ok) throw new Error();
      await inspect(
        new File([await response.blob()], "consultant-demo.csv", {
          type: "text/csv",
        }),
      );
    } catch {
      setError(
        new ApiError(
          "The example could not be loaded. Check the backend and retry.",
        ),
      );
    } finally {
      setBusy(false);
    }
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || !confirmed) return;
    setBusy(true);
    setError(null);
    try {
      const data = new FormData();
      data.append("file", file);
      data.append("options", JSON.stringify(options));
      const result = await api<{
        statement: Statement;
        already_imported: boolean;
      }>("/statements", { method: "POST", body: data });
      await onImported(result.statement, result.already_imported);
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e
          : new ApiError("Import failed. Nothing was imported."),
      );
    } finally {
      setBusy(false);
    }
  }
  const column = (label: string, field: keyof ImportOptions) => (
    <label className="field">
      {label}
      <select
        required
        value={options[field]}
        onChange={(e) => update(field, e.target.value)}
      >
        <option value="">Select column</option>
        {preview?.headers.map((h) => (
          <option key={h} value={h}>
            {h}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <section className="import-page">
      <button className="text-button" onClick={onCancel} disabled={busy}>
        <ArrowLeft size={16} /> Back to workspace
      </button>
      <div className="page-heading">
        <div>
          <div className="eyebrow">A CLEAR START</div>
          <h1>Bring your statement into focus.</h1>
          <p>Map the columns. Confirm the details. We’ll take it from there.</p>
        </div>
      </div>
      <div className="stepper" aria-label="Import progress">
        <span className="active">
          <b>{preview ? <Check size={14} /> : "1"}</b> Upload CSV
        </span>
        <i />
        <span className={preview ? "active" : ""}>
          <b>2</b> Confirm interpretation
        </span>
        <i />
        <span>
          <b>3</b> Review transactions
        </span>
      </div>
      {error && <ErrorNotice error={error} />}
      {!preview ? (
        <div className="import-columns">
          <div
            className="panel upload-panel"
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              if (!busy && e.dataTransfer.files[0])
                void inspect(e.dataTransfer.files[0]);
            }}
          >
            <div className="large-icon">
              <Upload size={30} />
            </div>
            <h2>A fresh perspective on your finances</h2>
            <p>
              Drop your CSV statement here, or choose a file.
              <br />
              Your records stay on this computer.
            </p>
            <label
              className={`button primary file-button ${busy ? "disabled" : ""}`}
            >
              <Upload size={16} />
              {busy ? "Reading statement…" : "Choose CSV file"}
              <input
                aria-label="Choose CSV file"
                disabled={busy}
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => {
                  if (e.target.files?.[0]) void inspect(e.target.files[0]);
                  e.target.value = "";
                }}
              />
            </label>
            <small>UTF-8 CSV · Up to 2 MiB · 5,000 transactions</small>
            <div className="sample-divider">
              <span>Just looking around?</span>
            </div>
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => void sample()}
            >
              <FileSpreadsheet size={17} /> Explore the synthetic example{" "}
              <ArrowRight size={16} />
            </button>
            <small>28 fictional transactions. Real categorization logic.</small>
          </div>
          <aside className="import-guide">
            <div className="eyebrow">BEFORE YOU IMPORT</div>
            <h2>A little clarity goes a long way.</h2>
            <div className="guide-item">
              <b>01</b>
              <div>
                <h3>Export a CSV</h3>
                <p>
                  Include a date, description, and amount—or separate debit and
                  credit columns.
                </p>
              </div>
            </div>
            <div className="guide-item">
              <b>02</b>
              <div>
                <h3>Confirm the meaning</h3>
                <p>
                  You choose the date format, currency, and which sign means
                  money out.
                </p>
              </div>
            </div>
            <div className="guide-item">
              <b>03</b>
              <div>
                <h3>Review with confidence</h3>
                <p>
                  Unclear transactions come to you. Nothing is silently guessed
                  or discarded.
                </p>
              </div>
            </div>
            <div className="privacy-note">
              <ShieldCheck size={21} />
              <p>
                Local by design. No banking connections, AI services, or cloud
                uploads.
              </p>
            </div>
            <a className="text-button" href="/api/demo" download>
              Download example CSV <ArrowRight size={14} />
            </a>
          </aside>
        </div>
      ) : (
        <form onSubmit={submit} className="mapping-layout">
          <div className="panel">
            <div className="panel-header">
              <div>
                <h2>Confirm your columns</h2>
                <p>
                  {file?.name} · {preview.row_count} transactions
                  {preview.blank_rows
                    ? ` · ${preview.blank_rows} blank lines ignored`
                    : ""}
                </p>
              </div>
              <button
                className="text-button"
                type="button"
                disabled={busy}
                onClick={() => {
                  setPreview(null);
                  setError(null);
                }}
              >
                Change file
              </button>
            </div>
            <div className="mapping-fields">
              {column("Transaction date", "date_column")}
              {column("Description / merchant", "description_column")}
              <label className="field">
                Amount layout
                <select
                  value={options.mode}
                  onChange={(e) => update("mode", e.target.value)}
                >
                  <option value="signed">One signed amount column</option>
                  <option value="split">Separate debit and credit</option>
                </select>
              </label>
              {options.mode === "signed" ? (
                column("Amount", "amount_column")
              ) : (
                <>
                  {column("Debit / money out", "debit_column")}
                  {column("Credit / money in", "credit_column")}
                </>
              )}
              <label className="field">
                Date format
                <select
                  value={options.date_format}
                  onChange={(e) => update("date_format", e.target.value)}
                >
                  <option value="iso">YYYY-MM-DD · 2026-09-15</option>
                  <option value="dmy">DD/MM/YYYY · 15/09/2026</option>
                  <option value="mdy">MM/DD/YYYY · 09/15/2026</option>
                </select>
              </label>
              <label className="field">
                Statement currency
                <select
                  value={options.currency}
                  onChange={(e) => update("currency", e.target.value)}
                >
                  {["USD", "PKR", "GBP", "EUR"].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
              {options.mode === "signed" && (
                <label className="field full-width">
                  Amount convention
                  <select
                    value={options.sign_convention}
                    onChange={(e) => update("sign_convention", e.target.value)}
                  >
                    <option value="negative_outgoing">
                      Negative = money out; positive = money in
                    </option>
                    <option value="positive_outgoing">
                      Positive = money out; negative = money in
                    </option>
                  </select>
                </label>
              )}
            </div>
            <div className="preview-area">
              <h3>
                Source preview{" "}
                <span>
                  First {preview.rows.length} rows, exactly as uploaded
                </span>
              </h3>
              <div className="table-scroll">
                <table className="preview-table">
                  <thead>
                    <tr>
                      <th>Row</th>
                      {preview.headers.map((h) => (
                        <th key={h}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row) => (
                      <tr key={row.source_row}>
                        <td>{row.source_row}</td>
                        {row.cells.map((cell, i) => (
                          <td key={i}>{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          <aside className="panel confirm-panel">
            <div className="large-icon small">
              <ShieldCheck size={24} />
            </div>
            <h2>Your interpretation matters.</h2>
            <p>We never infer a currency or silently reverse your amounts.</p>
            <div className="interpretation">
              <b>
                {options.currency} ·{" "}
                {options.mode === "split" ? "Debit / credit" : "Signed amounts"}
              </b>
              <span>
                {options.mode === "split"
                  ? "Debit leaves your account. Credit enters it."
                  : options.sign_convention === "negative_outgoing"
                    ? "−100.00 becomes money out."
                    : "+100.00 becomes money out."}
              </span>
              <span>
                {options.date_format === "iso"
                  ? "2026-09-15 → September 15"
                  : options.date_format === "dmy"
                    ? "03/04/2026 → April 3"
                    : "03/04/2026 → March 4"}
              </span>
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
              />
              <span>
                I checked the columns, date format, currency, and amount
                direction.
              </span>
            </label>
            <button
              className="button primary wide"
              disabled={!confirmed || busy}
              type="submit"
            >
              {busy ? (
                <LoaderCircle className="spin" size={17} />
              ) : (
                <ArrowRight size={17} />
              )}{" "}
              {busy ? "Validating every row…" : "Import & categorize"}
            </button>
            <div className="inline-note">
              <Info size={16} />
              <span>
                If any row is invalid, nothing is imported. You’ll get the exact
                rows to fix.
              </span>
            </div>
          </aside>
        </form>
      )}
    </section>
  );
}
