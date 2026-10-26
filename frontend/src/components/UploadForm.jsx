import { useRef, useState } from "react";

export default function UploadForm({ onUpload, loading }) {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [hint, setHint] = useState("");
  const inputRef = useRef(null);

  function pick(f) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setHint("Please choose a .csv file.");
      return;
    }
    setHint("");
    setFile(f);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    pick(e.dataTransfer.files?.[0]);
  }

  return (
    <section className="card">
      <div className="step-head">
        <span className="step">1</span>
        <div>
          <h2>Upload Statement (CSV)</h2>
          <p>Drag and drop your bank or credit card statement CSV, or choose a file. Fake data only.</p>
        </div>
      </div>

      <div
        className={dragging ? "dropzone dragging" : "dropzone"}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <svg className="drop-icon" width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M7 18a4.5 4.5 0 0 1-.6-8.96A6 6 0 0 1 17.9 8.5 4.5 4.5 0 0 1 17.5 18" />
          <path d="M12 12v8M9 15l3-3 3 3" />
        </svg>

        {file ? (
          <p className="drop-title file-name">{file.name}</p>
        ) : (
          <p className="drop-title">Drag &amp; drop your statement CSV here</p>
        )}
        <p className="drop-sub">{hint || "Supports .csv files · each row gets a category"}</p>

        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          hidden
          onChange={(e) => pick(e.target.files[0] || null)}
        />

        <div className="drop-actions">
          <button type="button" className="btn ghost" onClick={() => inputRef.current?.click()}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            </svg>
            Choose CSV
          </button>
          <button
            type="button"
            className="btn primary"
            disabled={!file || loading}
            onClick={() => onUpload(file)}
          >
            {loading ? (
              <>
                <span className="spinner" /> Processing...
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 16V4M7 9l5-5 5 5M5 20h14" />
                </svg>
                Categorize statement
              </>
            )}
          </button>
        </div>
      </div>
    </section>
  );
}
