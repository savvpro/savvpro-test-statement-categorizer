import React, { useRef, useState } from 'react';
import { getSampleCsv, uploadStatement } from '../api';

export default function UploadSection({ onUploadSuccess, loading, setLoading, error, setError, warnings, setWarnings }) {
  const [isDragActive, setIsDragActive] = useState(false);
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = async (file) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setError('Please select a valid .csv file.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      setWarnings([]);
      const data = await uploadStatement(file);
      onUploadSuccess(data);
    } catch (err) {
      setError(err.message || 'Error uploading file.');
    } finally {
      setLoading(false);
    }
  };

  const loadSample = async (formatType = 'standard') => {
    try {
      setLoading(true);
      setError(null);
      setWarnings([]);
      const csvText = await getSampleCsv(formatType);
      const filename = formatType === 'credit_card' ? 'sample_credit_card.csv' : 'sample_freelance_statement.csv';
      const file = new File([csvText], filename, { type: 'text/csv' });
      const data = await uploadStatement(file);
      onUploadSuccess(data);
    } catch (err) {
      setError(err.message || 'Error loading sample data.');
    } finally {
      setLoading(false);
    }
  };

  const downloadSampleTemplate = async (formatType) => {
    try {
      const csvText = await getSampleCsv(formatType);
      const blob = new Blob([csvText], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = formatType === 'credit_card' ? 'sample_credit_card.csv' : 'sample_statement.csv';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      setError('Could not download sample template.');
    }
  };

  return (
    <div style={{ marginBottom: '2rem' }}>
      {error && (
        <div className="alert alert-danger">
          <div>
            <strong>Error: </strong>
            <span>{error}</span>
          </div>
          <button
            onClick={() => setError(null)}
            style={{ background: 'none', border: 'none', color: '#fecdd3', cursor: 'pointer', fontSize: '1rem' }}
          >
            ✕
          </button>
        </div>
      )}

      {warnings && warnings.length > 0 && (
        <div className="alert alert-warning">
          <div>
            <strong>Warnings:</strong>
            <ul style={{ marginTop: '0.25rem', paddingLeft: '1.25rem' }}>
              {warnings.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>
          <button
            onClick={() => setWarnings([])}
            style={{ background: 'none', border: 'none', color: '#fde68a', cursor: 'pointer', fontSize: '1rem' }}
          >
            ✕
          </button>
        </div>
      )}

      <div
        className={`upload-card ${isDragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current && fileInputRef.current.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          style={{ display: 'none' }}
          onChange={handleFileChange}
        />

        <div className="upload-icon">📂</div>
        <h3 className="upload-title">
          {loading ? 'Processing & Categorizing Statement...' : 'Upload Bank or Credit Card Statement'}
        </h3>
        <p className="upload-subtitle">
          Drag and drop your statement CSV here, or click to browse. Supports Date, Description, and Amount or Debit/Credit columns.
        </p>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', color: 'var(--primary)' }}>
            <span className="spinner"></span>
            <span>Parsing transactions & running deterministic categorization brain...</span>
          </div>
        ) : (
          <div className="upload-actions" onClick={(e) => e.stopPropagation()}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => fileInputRef.current && fileInputRef.current.click()}
            >
              Choose CSV File
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => loadSample('standard')}
              title="Instantly test with pre-built freelance bank statement"
            >
              Load Freelancer Sample
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => loadSample('credit_card')}
              title="Load Debit/Credit multi-column format"
            >
              Load Credit Card Sample
            </button>
            <button
              type="button"
              className="btn btn-outline"
              onClick={() => downloadSampleTemplate('standard')}
              title="Download empty CSV template for your own transactions"
            >
              Download Example CSV
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
