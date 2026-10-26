import { useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  FileSpreadsheet,
  Upload,
  X,
} from "lucide-react";
import { api, money, title, uploadData } from "./api";
import type { ImportSettings, Inspection, Preview } from "./types";

interface Props {
  onClose: () => void;
  onImported: () => Promise<void>;
}
export default function ImportDialog({ onClose, onImported }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [settings, setSettings] = useState<ImportSettings>({
    account: "",
    account_type: "credit_card",
    currency: "PKR",
    date_order: "day_first",
    amount_direction: "out_positive",
    mapping: {},
  });
  const ref = useRef<HTMLInputElement>(null);
  function change<K extends keyof ImportSettings>(
    key: K,
    value: ImportSettings[K],
  ) {
    setSettings((old) => ({ ...old, [key]: value }));
    setPreview(null);
  }
  async function inspect(selected: File) {
    setBusy(true);
    setError("");
    setPreview(null);
    setInspection(null);
    setFile(selected);
    try {
      const result = await api<Inspection>("/imports/inspect", {
        method: "POST",
        body: uploadData(selected),
      });
      setInspection(result);
      setSettings((old) => ({ ...old, mapping: result.mapping }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function validate() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      setPreview(
        await api<Preview>("/imports/preview", {
          method: "POST",
          body: uploadData(file, settings),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function commit() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      await api("/imports", {
        method: "POST",
        body: uploadData(file, settings),
      });
      await onImported();
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !busy) onClose();
      }}
    >
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="import-title"
        className="import-dialog"
      >
        <header className="dialog-header">
          <div>
            <h2 id="import-title">Upload a statement</h2>
            <p>Check the rows before they enter your books.</p>
          </div>
          <button
            className="icon-button"
            aria-label="Close upload"
            disabled={busy}
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </header>
        <div className="steps">
          <span className="current">1. Select file</span>
          <ArrowRight size={14} />
          <span className={inspection ? "current" : ""}>2. Confirm format</span>
          <ArrowRight size={14} />
          <span className={preview ? "current" : ""}>3. Import</span>
        </div>
        <input
          ref={ref}
          className="sr-only"
          type="file"
          accept=".csv,.xlsx,.pdf"
          aria-label="Statement file"
          onChange={(e) => {
            if (e.target.files?.[0]) void inspect(e.target.files[0]);
          }}
        />
        <button
          className="dropzone"
          disabled={busy}
          onClick={() => ref.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            if (e.dataTransfer.files[0] && !busy)
              void inspect(e.dataTransfer.files[0]);
          }}
        >
          <span className="upload-icon">
            <Upload size={24} />
          </span>
          <strong>
            {file ? file.name : "Choose a statement or drop it here"}
          </strong>
          <span>CSV, XLSX or supported text PDF · up to 5 MB</span>
        </button>
        <p className="sample-links">
          Try fake data:{" "}
          <a href="/api/samples/developer-credit-card.csv">Credit card</a>
          <a href="/api/samples/developer-bank.csv">Bank</a>
          <a href="/api/samples/developer-wallet.csv">Wallet</a>
          <a href="/api/samples/developer-international.csv">International</a>
          <a href="/api/samples/developer-statement.pdf">PDF</a>
          <a href="/api/samples/developer-statement.xlsx">XLSX</a>
        </p>
        {error ? (
          <div className="error" role="alert">
            {error}
          </div>
        ) : null}
        {inspection ? (
          <>
            <div className="form-grid">
              <label>
                Account name
                <input
                  autoFocus
                  required
                  maxLength={80}
                  value={settings.account}
                  placeholder="e.g. My business credit card"
                  onChange={(e) => change("account", e.target.value)}
                />
              </label>
              <label>
                Account type
                <select
                  value={settings.account_type}
                  onChange={(e) => change("account_type", e.target.value)}
                >
                  <option value="credit_card">Credit card</option>
                  <option value="bank">Bank account</option>
                  <option value="wallet">Digital wallet</option>
                  <option value="international">International account</option>
                </select>
              </label>
              <label>
                Default currency
                <select
                  value={settings.currency}
                  onChange={(e) => change("currency", e.target.value)}
                >
                  {["PKR", "USD", "EUR", "GBP", "AED"].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
              <label>
                Date order
                <select
                  value={settings.date_order}
                  onChange={(e) => change("date_order", e.target.value)}
                >
                  <option value="day_first">Day / month / year</option>
                  <option value="month_first">Month / day / year</option>
                </select>
              </label>
              <label className="wide">
                Signed amount convention
                <select
                  value={settings.amount_direction}
                  onChange={(e) => change("amount_direction", e.target.value)}
                >
                  <option value="out_positive">
                    Positive = money out; negative = money in
                  </option>
                  <option value="in_positive">
                    Positive = money in; negative = money out
                  </option>
                </select>
                <small>
                  Separate debit/credit columns always use nonnegative values:
                  debit is money out.
                </small>
              </label>
            </div>
            <h3>
              Map your columns{" "}
              <span className="muted">{inspection.row_count} source rows</span>
            </h3>
            <div className="mapping-grid">
              {Object.keys(inspection.mapping).map((key) => (
                <label key={key}>
                  {title(key)}
                  {["date", "description"].includes(key) ? " *" : ""}
                  <select
                    aria-label={`Map ${key}`}
                    value={settings.mapping[key] || ""}
                    onChange={(e) =>
                      change("mapping", {
                        ...settings.mapping,
                        [key]: e.target.value,
                      })
                    }
                  >
                    <option value="">Not mapped</option>
                    {inspection.headers.map((h) => (
                      <option key={h}>{h}</option>
                    ))}
                  </select>
                </label>
              ))}
            </div>
            <p className="hint">
              Map either Amount or both Debit and Credit. Preview must reconcile
              every row.
            </p>
            <div className="preview-table">
              <table>
                <thead>
                  <tr>
                    {inspection.headers.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {inspection.rows.slice(0, 3).map((row, i) => (
                    <tr key={i}>
                      {row.map((v, j) => (
                        <td key={j}>{v || "—"}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {preview ? (
              <div
                className={preview.errors.length ? "error" : "success"}
                role="status"
              >
                <strong>
                  {preview.valid_count} of {preview.source_count} rows valid
                </strong>
                {preview.errors.length ? (
                  <>
                    <p>
                      <AlertTriangle size={14} /> Import blocked. Fix these rows
                      in your source file and select it again.
                    </p>
                    <ul>
                      {preview.errors.map((e) => (
                        <li key={e.row}>
                          Row {e.row}: {e.message}
                        </li>
                      ))}
                    </ul>
                  </>
                ) : (
                  <p>
                    {Object.entries(preview.summary)
                      .map(([c, a]) => `${c} net movement: ${money(a, c)}`)
                      .join(" · ")}
                    . Negative means net money in.
                  </p>
                )}
              </div>
            ) : null}
            <footer className="dialog-footer">
              <span>
                <FileSpreadsheet size={16} /> Original descriptions are
                preserved.
              </span>
              {preview && !preview.errors.length ? (
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() => void commit()}
                >
                  {busy
                    ? "Importing…"
                    : `Import ${preview.valid_count} transactions`}
                  <ArrowRight size={16} />
                </button>
              ) : (
                <button
                  className="primary"
                  disabled={busy || !settings.account.trim()}
                  onClick={() => void validate()}
                >
                  {busy ? "Reading statement…" : "Validate & preview"}
                  <ArrowRight size={16} />
                </button>
              )}
            </footer>
          </>
        ) : (
          <p className="hint">
            PDF support is limited to the supplied synthetic v1 layout. For
            other layouts, use a CSV/XLSX export. Scans are not supported.
          </p>
        )}
        {!inspection && busy ? (
          <p role="status">Reading your statement…</p>
        ) : null}
      </section>
    </div>
  );
}
