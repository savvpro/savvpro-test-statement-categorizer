import { useState } from "react";

export function UploadPanel({ onUpload, loading, fileName }) {
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files) => files?.[0] && onUpload(files[0]);

  return (
    <label
      className={`dropzone ${dragging ? "dragging" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
    >
      <input type="file" accept=".csv,text/csv" disabled={loading}
        onChange={(e) => { handleFiles(e.target.files); e.target.value = ""; }} />
      <strong>{loading ? "Reading statement…" : "Drop a CSV statement here or click to upload"}</strong>
      <span>{fileName ? `Current: ${fileName}` : "Exports from most UK banks work as-is"}</span>
    </label>
  );
}
