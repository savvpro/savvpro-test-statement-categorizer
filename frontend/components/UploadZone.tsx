import { useState } from "react";

type Props = {
  uploading: boolean;
  error: string | null;
  fileName: string | null;
  skipped: string[];
  onFile: (file: File | undefined) => void;
};

export function UploadZone({ uploading, error, fileName, skipped, onFile }: Props) {
  const [dragging, setDragging] = useState(false);

  return (
    <section className="panel" aria-label="Upload statement">
      <label
        className={`dropzone${dragging ? " dragging" : ""}${uploading ? " busy" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (!uploading) onFile(e.dataTransfer.files[0]);
        }}
      >
        <input
          type="file"
          accept=".csv,text/csv"
          disabled={uploading}
          onChange={(e) => {
            onFile(e.target.files?.[0]);
            e.target.value = "";
          }}
        />
        {uploading ? <span className="spinner" aria-hidden="true" /> : <span className="dz-icon" aria-hidden="true">↑</span>}
        <span className="dz-text">
          <strong>{uploading ? "Reading statement…" : "Drop a bank statement here, or browse"}</strong>
          <span className="muted">
            {fileName ? `Last file: ${fileName}` : "CSV with Date, Description, Debit, Credit, Balance. Max 1 MB."}
          </span>
        </span>
      </label>
      {error && <p className="error" role="alert">{error}</p>}
      {skipped.length > 0 && (
        <details className="warn">
          <summary>{skipped.length} bad row(s) skipped</summary>
          <ul>{skipped.map((s) => <li key={s}>{s}</li>)}</ul>
        </details>
      )}
    </section>
  );
}
