import React from 'react';
import { Landmark, HelpCircle, FileText, Download, RotateCcw, CheckCircle2, AlertCircle } from 'lucide-react';

interface HeaderProps {
  backendConnected: boolean;
  onOpenExplain: () => void;
  onLoadDemo: () => void;
  onReset: () => void;
  hasTransactions: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  backendConnected,
  onOpenExplain,
  onLoadDemo,
  onReset,
  hasTransactions,
}) => {
  return (
    <header className="app-header">
      <div className="brand-section">
        <div className="brand-icon">
          <Landmark size={24} />
        </div>
        <div>
          <h1 className="brand-title">Freelance Ledger</h1>
          <div className="brand-subtitle">
            <span>Deterministic Statement Categorizer</span>
            <span>•</span>
            {backendConnected ? (
              <span style={{ color: 'var(--color-success)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle2 size={13} /> Engine Online
              </span>
            ) : (
              <span style={{ color: 'var(--color-danger)', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                <AlertCircle size={13} /> Offline
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="header-actions">
        <button
          className="btn btn-outline"
          onClick={onOpenExplain}
          title="Learn how deterministic rules categorize your statement without external AI"
        >
          <HelpCircle size={16} />
          <span>How It Works</span>
        </button>

        <a
          href="/sample_data/statement_template.csv"
          download="statement_template.csv"
          className="btn btn-secondary"
          title="Download sample CSV format template"
        >
          <Download size={16} />
          <span>CSV Template</span>
        </a>

        {!hasTransactions ? (
          <button className="btn btn-primary" onClick={onLoadDemo}>
            <FileText size={16} />
            <span>Load Demo Statement</span>
          </button>
        ) : (
          <button className="btn btn-outline" onClick={onReset} title="Clear statement and start fresh">
            <RotateCcw size={16} />
            <span>Reset</span>
          </button>
        )}
      </div>
    </header>
  );
};
