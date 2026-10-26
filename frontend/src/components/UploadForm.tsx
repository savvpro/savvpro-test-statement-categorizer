import { useId, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api, ApiError, errorMessage } from "../api";
import type { AmountMode, DateFormat, RowError } from "../types";
import { Icon } from "./Icon";

export function UploadForm({
  onImported,
  onCancel,
}: {
  onImported: (id: string, reused: boolean) => Promise<void>;
  onCancel?: () => void;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [amountMode, setAmountMode] = useState<AmountMode>("bank_signed");
  const [dateFormat, setDateFormat] = useState<DateFormat>("iso");
  const [currency, setCurrency] = useState("USD");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [rowErrors, setRowErrors] = useState<RowError[]>([]);
  const [dragging, setDragging] = useState(false);

  function chooseFile(next?: File) {
    setError("");
    setRowErrors([]);
    if (!next) return;
    if (!next.name.toLowerCase().endsWith(".csv")) {
      setError(
        "Choose a CSV file. PDF and image statements are not supported.",
      );
      return;
    }
    if (next.size > 5 * 1024 * 1024) {
      setError("Choose a file smaller than 5 MiB.");
      return;
    }
    setFile(next);
  }

  async function submit(event?: FormEvent, sample = false) {
    event?.preventDefault();
    if (!sample && !file) {
      setError("Choose a statement to import.");
      return;
    }
    setBusy(true);
    setError("");
    setRowErrors([]);
    try {
      const selected = sample ? await api.sample() : file!;
      const body = new FormData();
      body.append("file", selected);
      body.append("amount_mode", sample ? "bank_signed" : amountMode);
      body.append("date_format", sample ? "iso" : dateFormat);
      body.append("currency", sample ? "USD" : currency);
      const result = await api.import(body);
      await onImported(result.id, result.reused);
    } catch (err) {
      setError(errorMessage(err));
      if (err instanceof ApiError) setRowErrors(err.rows);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="upload-card" aria-labelledby={`${id}-title`}>
      <div className="section-top">
        <div>
          <span className="eyebrow">START WITH YOUR STATEMENT</span>
          <h2 id={`${id}-title`}>A little less admin. A lot more clarity.</h2>
        </div>
        {onCancel && (
          <button
            className="icon-button"
            onClick={onCancel}
            aria-label="Close upload form"
            disabled={busy}
          >
            <Icon name="close" />
          </button>
        )}
      </div>
      <p className="muted">
        Upload a business-account CSV. We’ll organize the familiar and flag the
        uncertain.
      </p>
      <form onSubmit={submit}>
        <fieldset disabled={busy} className="form-fields">
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
              if (!busy) chooseFile(event.dataTransfer.files[0]);
            }}
          >
            <span className="upload-symbol">
              <Icon name={file ? "file" : "upload"} size={26} />
            </span>
            <strong>{file ? file.name : "Drop your statement here"}</strong>
            <span className="muted small">
              {file
                ? `${(file.size / 1024).toFixed(1)} KB · ready to import`
                : "CSV · up to 5 MiB · 5,000 transactions"}
            </span>
            <button
              type="button"
              className="button secondary"
              onClick={() => input.current?.click()}
            >
              {file ? "Choose another file" : "Browse files"}
            </button>
            <input
              ref={input}
              type="file"
              accept=".csv,text/csv"
              className="sr-only"
              aria-label="Statement CSV file"
              onChange={(event) => chooseFile(event.target.files?.[0])}
            />
          </div>
          <div className="form-grid">
            <label>
              Amount format
              <select
                value={amountMode}
                onChange={(event) =>
                  setAmountMode(event.target.value as AmountMode)
                }
              >
                <option value="bank_signed">Bank · negative = money out</option>
                <option value="card_signed">Card · positive = charges</option>
                <option value="debit_credit">
                  Separate debit / credit columns
                </option>
              </select>
            </label>
            <label>
              Date format
              <select
                value={dateFormat}
                onChange={(event) =>
                  setDateFormat(event.target.value as DateFormat)
                }
              >
                <option value="iso">YYYY-MM-DD</option>
                <option value="day_first">DD/MM/YYYY</option>
                <option value="month_first">MM/DD/YYYY</option>
              </select>
            </label>
            <label>
              Currency
              <select
                value={currency}
                onChange={(event) => setCurrency(event.target.value)}
              >
                {["USD", "EUR", "GBP", "PKR", "CAD", "AUD"].map((value) => (
                  <option key={value}>{value}</option>
                ))}
              </select>
            </label>
          </div>
          <p className="small muted">
            <Icon name="info" size={15} /> Check the sign convention in your
            export. Imports use one currency; amounts are never converted.
          </p>
          {error && (
            <div className="error-box" role="alert">
              <strong>{error}</strong>
              {rowErrors.length > 0 && (
                <ul>
                  {rowErrors.map((row) => (
                    <li key={row.row}>
                      Row {row.row}: {row.message}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          <div className="upload-actions">
            <button type="submit" className="button primary">
              <Icon name="upload" size={17} />
              {busy ? "Reading statement…" : "Import statement"}
            </button>
            <button
              type="button"
              className="button text-button"
              onClick={() => submit(undefined, true)}
            >
              Try a sample statement <Icon name="arrow" size={17} />
            </button>
          </div>
        </fieldset>
      </form>
      <div className="upload-foot">
        <Icon name="shield" size={17} />
        <span>
          Processed by your local Python server. No AI or bank connections.
        </span>
        <a href="/api/sample" download>
          Download sample CSV
        </a>
      </div>
    </section>
  );
}
