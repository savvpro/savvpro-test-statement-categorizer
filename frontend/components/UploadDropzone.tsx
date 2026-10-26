"use client";

import { useRef, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";
import { cx } from "./ui";

export const MAX_UPLOAD_BYTES = 5 * 1024 * 1024;

/** Client-side guard; the backend re-checks and its `detail` is shown if it disagrees. */
export function validateCsv(file: File): string | null {
  if (!file.name.toLowerCase().endsWith(".csv")) {
    return `"${file.name}" is not a .csv file. Export your statement as CSV and try again.`;
  }
  if (file.size > MAX_UPLOAD_BYTES) {
    const mb = (file.size / (1024 * 1024)).toFixed(1);
    return `"${file.name}" is ${mb} MB. The limit is 5 MB.`;
  }
  if (file.size === 0) return `"${file.name}" is empty.`;
  return null;
}

export function UploadDropzone({
  busy,
  error,
  onFile,
  onSample,
}: {
  busy: "upload" | "sample" | null;
  error: string | null;
  onFile: (file: File) => void;
  onSample: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const disabled = busy !== null;

  return (
    <section aria-label="Upload a statement">
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-disabled={disabled}
        aria-describedby="dropzone-help"
        onClick={() => !disabled && inputRef.current?.click()}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file && !disabled) onFile(file);
        }}
        className={cx(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed px-6 py-16 text-center transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:py-24",
          dragging ? "border-accent bg-accent-soft" : "border-line-strong bg-card hover:border-accent/60",
          disabled && "cursor-progress opacity-70",
        )}
      >
        <span
          className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-accent-soft text-accent"
          aria-hidden="true"
        >
          {busy === "upload" ? <Loader2 size={22} className="animate-spin" /> : <FileUp size={22} strokeWidth={1.75} />}
        </span>
        <p className="mt-4 text-base font-semibold text-ink">
          {busy === "upload" ? "Reading your statement..." : "Drop CSV here"}
        </p>
        <p id="dropzone-help" className="mt-1 text-sm text-muted">
          or click to choose a file. Only .csv, max 5 MB.
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,text/csv"
          className="sr-only"
          tabIndex={-1}
          onChange={(e) => {
            const file = e.target.files?.[0];
            e.target.value = "";
            if (file) onFile(file);
          }}
        />
      </div>

      {error ? (
        <p role="alert" className="mt-4 rounded-lg border border-red/25 bg-red-soft px-3 py-2 text-sm text-red">
          {error}
        </p>
      ) : null}

      <div className="mt-4 flex flex-col items-center gap-1 text-sm text-muted sm:flex-row sm:justify-center">
        <span>No statement handy?</span>
        <button
          type="button"
          onClick={onSample}
          disabled={disabled}
          className="inline-flex items-center gap-1.5 font-medium text-accent underline-offset-4 hover:underline disabled:opacity-60"
        >
          {busy === "sample" ? <Loader2 size={14} className="animate-spin" aria-hidden="true" /> : null}
          Try with sample statement
        </button>
      </div>
    </section>
  );
}
