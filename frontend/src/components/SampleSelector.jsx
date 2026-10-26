import React, { useRef } from 'react';
import { UploadCloud, FileText, Check, Sparkles, AlertCircle } from 'lucide-react';

export default function SampleSelector({
  samples,
  activeSampleId,
  onSelectSample,
  onFileUpload,
  isLoading,
}) {
  const fileInputRef = useRef(null);

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Sample Statement Presets */}
      <div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Sparkles size={16} color="#818cf8" />
            <h2 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              1-Click Realistic Statement Presets
            </h2>
          </div>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Curated messy statements testing edge cases
          </span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
          {samples.map((sample) => {
            const isSelected = activeSampleId === sample.id;
            return (
              <div
                key={sample.id}
                onClick={() => !isLoading && onSelectSample(sample.id)}
                className="glass-panel"
                style={{
                  padding: '16px',
                  cursor: isLoading ? 'wait' : 'pointer',
                  border: isSelected ? '1px solid var(--accent-indigo)' : '1px solid var(--border-subtle)',
                  background: isSelected ? 'rgba(99, 102, 241, 0.1)' : 'var(--bg-card)',
                  position: 'relative',
                  transition: 'all 0.2s ease',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 8 }}>
                  <div>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                      {sample.title}
                    </h3>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {sample.subtitle}
                    </span>
                  </div>
                  {isSelected && (
                    <div style={{
                      width: 20,
                      height: 20,
                      borderRadius: '50%',
                      background: 'var(--accent-indigo)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}>
                      <Check size={12} color="#fff" />
                    </div>
                  )}
                </div>

                <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: 10, lineHeight: 1.4 }}>
                  {sample.description}
                </p>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {sample.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      style={{
                        fontSize: '0.68rem',
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: 6,
                        background: 'rgba(255, 255, 255, 0.05)',
                        border: '1px solid var(--border-subtle)',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                  <span style={{
                    fontSize: '0.68rem',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: 6,
                    background: 'rgba(99, 102, 241, 0.12)',
                    color: '#818cf8',
                    marginLeft: 'auto',
                  }}>
                    {sample.transaction_count} rows
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Or Drag & Drop Upload Dropzone */}
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => fileInputRef.current && fileInputRef.current.click()}
        className="glass-panel"
        style={{
          padding: '20px',
          border: '2px dashed var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
          cursor: 'pointer',
          background: 'rgba(16, 21, 33, 0.4)',
          transition: 'all 0.2s ease',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent-indigo)')}
        onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-subtle)')}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,text/csv"
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files && e.target.files[0]) {
              onFileUpload(e.target.files[0]);
            }
          }}
        />
        <div style={{
          width: 40,
          height: 40,
          borderRadius: 10,
          background: 'rgba(99, 102, 241, 0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}>
          <UploadCloud size={20} color="#818cf8" />
        </div>
        <div>
          <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Or Drop your own Bank or Credit Card CSV Statement here
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Autodetects Chase, Amex, Bank of America, Wells Fargo, Capital One, or generic CSV formats.
          </div>
        </div>
      </div>
    </div>
  );
}
