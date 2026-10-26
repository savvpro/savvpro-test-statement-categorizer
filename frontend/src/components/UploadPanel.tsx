import { useRef, useState } from "react";
import type { Sample, SignConvention } from "../types";

interface Props {
  samples: Sample[];
  busy: boolean;
  onUpload: (file: File, signConvention: SignConvention) => void;
  onSample: (name: string) => void;
}

const CONVENTIONS: { value: SignConvention; label: string }[] = [
  { value: "auto", label: "Detect automatically" },
  { value: "negative_is_spending", label: "Spending is negative (most banks)" },
  { value: "positive_is_spending", label: "Spending is positive (many card exports)" },
];

export function UploadPanel({ samples, busy, onUpload, onSample }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [convention, setConvention] = useState<SignConvention>("auto");
  const [dragging, setDragging] = useState(false);

  function submit() {
    if (!file) return;
    onUpload(file, convention);
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <section className="panel" aria-labelledby="upload-title">
      <h2 id="upload-title">Upload a statement</h2>
      <label
        className={`dropzone${dragging ? " dropzone--active" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const dropped = e.dataTransfer.files[0];
          if (dropped) setFile(dropped);
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.txt,.ofx,.qfx"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <span className="dropzone__title">{file ? file.name : "Choose or drop a file"}</span>
        <span className="muted">CSV, OFX or QFX export from your bank or card</span>
      </label>

      <label className="field">
        <span>Amount signs</span>
        <select
          value={convention}
          onChange={(e) => setConvention(e.target.value as SignConvention)}
        >
          {CONVENTIONS.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </label>

      <button className="btn btn--primary btn--block" disabled={!file || busy} onClick={submit}>
        {busy ? "Sorting…" : "Sort my transactions"}
      </button>

      {samples.length > 0 && (
        <div className="samples">
          <p className="muted">No statement handy? Try a fake one:</p>
          {samples.map((s) => (
            <button
              key={s.name}
              className="btn btn--ghost btn--block"
              disabled={busy}
              title={s.description}
              onClick={() => onSample(s.name)}
            >
              {s.title}
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
