import { useState } from "react";

export default function UploadPanel({ onUpload, loading }) {
  const [file, setFile] = useState(null);
  const [flip, setFlip] = useState(false);

  function submit(e) {
    e.preventDefault();
    if (file) onUpload(file, flip);
  }

  return (
    <form className="panel upload" onSubmit={submit}>
      <input
        type="file"
        accept=".csv,text/csv"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        aria-label="Statement CSV file"
      />
      <label className="check">
        <input type="checkbox" checked={flip} onChange={(e) => setFlip(e.target.checked)} />
        This card lists purchases as positive numbers
      </label>
      <button type="submit" disabled={!file || loading}>
        {loading ? "Working…" : "Categorize"}
      </button>
    </form>
  );
}