import { useRef, useState } from 'react';
import { ArrowUpFromLine, FileSpreadsheet, CheckCircle2, X, LoaderCircle } from 'lucide-react';

export default function UploadPanel({ onUpload, busy }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');

  function selectFile(candidate) {
    setError('');
    if (!candidate) return;
    if (!/\.(csv|tsv)$/i.test(candidate.name)) {
      setError('Please choose a CSV or TSV statement file.');
      return;
    }
    if (candidate.size > 15 * 1024 * 1024) {
      setError('This file is larger than 15 MB. Please choose a smaller statement.');
      return;
    }
    setFile(candidate);
  }

  async function submit() {
    if (!file) return;
    const ok = await onUpload(file);
    if (ok) { setFile(null); if (inputRef.current) inputRef.current.value = ''; }
  }

  return <section className="upload-card">
    <div className="section-heading"><div><span className="eyebrow">GET STARTED</span><h2>Import a statement</h2><p>Upload a CSV statement to categorize transactions automatically.</p></div><span className="secure-chip"><CheckCircle2 size={14}/> Private by design</span></div>
    <div className={`dropzone ${dragging ? 'is-dragging' : ''}`} onDragOver={e => {e.preventDefault(); setDragging(true);}} onDragLeave={() => setDragging(false)} onDrop={e => {e.preventDefault(); setDragging(false); selectFile(e.dataTransfer.files?.[0]);}}>
      <input ref={inputRef} type="file" accept=".csv,.tsv,text/csv,text/tab-separated-values" hidden onChange={e => selectFile(e.target.files?.[0])}/>
      <div className="upload-icon"><ArrowUpFromLine size={23}/></div>
      <strong>Drop your statement here</strong><span>or <button className="text-button" onClick={() => inputRef.current?.click()}>browse files</button> from your computer</span>
      <small>CSV or TSV · Max 15 MB</small>
    </div>
    {error && <p className="inline-error">{error}</p>}
    {file && <div className="selected-file"><FileSpreadsheet size={20}/><div className="file-details"><strong>{file.name}</strong><span>{(file.size / 1024).toFixed(1)} KB</span></div><button className="icon-button" aria-label="Remove selected file" onClick={() => {setFile(null); if(inputRef.current) inputRef.current.value='';}}><X size={17}/></button></div>}
    <div className="upload-footer"><p><span className="privacy-dot"/> Your statement is processed by your local backend.</p><button className="button button-primary" disabled={!file || busy} onClick={submit}>{busy ? <><LoaderCircle className="spin" size={16}/> Processing…</> : <><ArrowUpFromLine size={16}/> Categorize statement</>}</button></div>
  </section>;
}
