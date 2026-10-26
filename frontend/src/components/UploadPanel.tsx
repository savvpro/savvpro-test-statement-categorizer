import { useState } from "react";
import type { ChangeEvent, DragEvent, FormEvent } from "react";
import { useCountdown } from "../hooks/useCountdown";
import type { FriendlyError } from "../errors";
import { acceptedFormatsLabel, checkFile, conventionLabel, formatMb } from "../format";
import type { AmountConvention, AppConfig } from "../types";
import { AlertIcon, UploadIcon } from "./Icons";

interface Props {
  onUpload: (file: File, convention: AmountConvention) => void | Promise<void>;
  loading: boolean;
  error: FriendlyError | null;
  config: AppConfig;
  /** Epoch ms until which uploads are blocked by the server's rate limit. */
  retryUntil?: number | null;
}

const CONVENTIONS: AmountConvention[] = ["auto", "negative_is_spending", "positive_is_spending"];

export function UploadPanel({ onUpload, loading, error, config, retryUntil = null }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [convention, setConvention] = useState<AmountConvention>("auto");
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const waitSeconds = useCountdown(retryUntil);

  function choose(next: File | undefined) {
    if (!next) return;
    const problem = checkFile(next, config);
    if (problem) {
      setFile(null);
      setLocalError(problem);
      return;
    }
    setLocalError(null);
    setFile(next);
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    choose(e.target.files?.[0]);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    if (loading) return;
    choose(e.dataTransfer.files?.[0]);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (waitSeconds > 0 || loading) return;
    if (!file) {
      setLocalError("Choose a statement file first.");
      return;
    }
    void onUpload(file, convention);
  }

  const blocked = waitSeconds > 0;
  const accept = config.accepted_extensions.join(",");
  const hint = `${acceptedFormatsLabel(config.accepted_extensions)}. Up to ${formatMb(config.max_upload_mb)} MB.`;

  return (
    <section className="card" aria-labelledby="upload-heading">
      <h2 id="upload-heading">Upload a statement</h2>
      <form onSubmit={handleSubmit}>
        <div
          className={`dropzone ${dragging ? "dragging" : ""}`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          <span className="dropzone-icon">
            <UploadIcon />
          </span>
          <p className="dropzone-title">Drag and drop your statement here, or</p>
          <input
            id="statement-file"
            className="file-input"
            type="file"
            accept={accept}
            onChange={handleChange}
            disabled={loading}
          />
          <label htmlFor="statement-file" className="button">
            Choose file
          </label>
          <p className="muted hint">{hint}</p>
          <p className="file-name" aria-live="polite">
            {file ? `Selected: ${file.name}` : "No file selected"}
          </p>
        </div>

        <details className="advanced">
          <summary>Advanced</summary>
          <div className="field">
            <label htmlFor="amount-convention">Amount convention</label>
            <select
              id="amount-convention"
              value={convention}
              onChange={(e) => setConvention(e.target.value as AmountConvention)}
              disabled={loading}
            >
              {CONVENTIONS.map((c) => (
                <option key={c} value={c}>
                  {conventionLabel(c)}
                </option>
              ))}
            </select>
            <p className="muted hint">
              Whether spending appears as negative or positive numbers in your file.
            </p>
          </div>
        </details>

        <div role="alert">
          {localError && (
            <p className="alert error">
              <AlertIcon />
              <span>{localError}</span>
            </p>
          )}
          {!localError && error && (
            <p className="alert error">
              <AlertIcon />
              <span>
                <strong>{error.title}.</strong> {error.message}
              </span>
            </p>
          )}
          {blocked && (
            <p className="alert error">
              <AlertIcon />
              <span>Too many requests, try again in {waitSeconds} s.</span>
            </p>
          )}
        </div>

        <button type="submit" className="button primary" disabled={loading || blocked}>
          {loading ? "Categorizing…" : "Categorize statement"}
        </button>
      </form>
    </section>
  );
}
