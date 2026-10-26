import { useState } from "react";

export default function UploadForm({ onUpload, busy }) {
  const [file, setFile] = useState(null);
  const [chargesArePositive, setChargesArePositive] = useState(true);

  function submit(event) {
    event.preventDefault();
    if (file) onUpload(file, chargesArePositive);
  }

  return (
    <form className="upload" onSubmit={submit}>
      <label className="field">
        <span>Statement file (.csv)</span>
        <input type="file" accept=".csv" onChange={(e) => setFile(e.target.files[0] || null)} />
      </label>
      <label className="field">
        <span>In my file, a purchase shows as</span>
        <select value={String(chargesArePositive)} onChange={(e) => setChargesArePositive(e.target.value === "true")}>
          <option value="true">a positive number (most credit cards)</option>
          <option value="false">a negative number (most bank accounts)</option>
        </select>
      </label>
      <button type="submit" disabled={!file || busy}>
        {busy ? "Sorting…" : "Sort my statement"}
      </button>
    </form>
  );
}
