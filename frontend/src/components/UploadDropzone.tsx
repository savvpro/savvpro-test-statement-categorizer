import React, { useRef, useState } from 'react';
import { UploadCloud, FileSpreadsheet, Play, AlertCircle, ShieldCheck } from 'lucide-react';

interface UploadDropzoneProps {
  onFileUpload: (file: File) => void;
  onLoadDemo: () => void;
  isLoading: boolean;
  errorMessage?: string | null;
}

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({
  onFileUpload,
  onLoadDemo,
  isLoading,
  errorMessage,
}) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.toLowerCase().endsWith('.csv')) {
        onFileUpload(droppedFile);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onFileUpload(e.target.files[0]);
    }
  };

  return (
    <div
      className={`dropzone-card ${isDragActive ? 'drag-active' : ''}`}
      onDragEnter={handleDrag}
      onDragOver={handleDrag}
      onDragLeave={handleDrag}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        className="hidden-file-input"
        onChange={handleFileChange}
      />

      <div className="dropzone-icon-wrapper">
        <UploadCloud size={32} />
      </div>

      <h2 className="dropzone-title">Upload Bank or Credit Card Statement</h2>
      <p className="dropzone-text">
        Drag and drop your statement CSV here, or browse from your computer.
        Transactions will be processed locally via deterministic rule heuristics — no financial data is ever sent to an external AI service.
      </p>

      {errorMessage && (
        <div style={{ maxWidth: '600px', margin: '0 auto 20px', padding: '12px 16px', background: 'var(--color-danger-bg)', border: '1px solid var(--color-danger)', borderRadius: 'var(--radius-md)', color: '#fca5a5', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      <div className="dropzone-cta-group">
        <button
          className="btn btn-primary"
          onClick={() => fileInputRef.current?.click()}
          disabled={isLoading}
        >
          <FileSpreadsheet size={16} />
          <span>{isLoading ? 'Processing Statement...' : 'Choose CSV File'}</span>
        </button>

        <button
          className="btn btn-secondary"
          onClick={onLoadDemo}
          disabled={isLoading}
        >
          <Play size={16} />
          <span>Load Synthetic Freelancer Demo</span>
        </button>
      </div>

      <div style={{ marginTop: '24px', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '16px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
          <ShieldCheck size={14} color="#10b981" /> 100% Deterministic Engine
        </span>
        <span>•</span>
        <span>Supports Signed Amount or Debit/Credit columns</span>
        <span>•</span>
        <span>Schedule C Ready</span>
      </div>
    </div>
  );
};
