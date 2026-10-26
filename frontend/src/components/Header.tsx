import React from "react";
import { Download, Upload, Cpu, CheckCircle } from "lucide-react";

interface HeaderProps {
  filename?: string;
  onExport: () => void;
  onReset: () => void;
  isExportDisabled: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  filename,
  onExport,
  onReset,
  isExportDisabled,
}) => {
  return (
    <header className="app-header">
      <div className="header-left">
        <div className="logo-badge">
          <Cpu size={24} className="logo-icon" />
        </div>
        <div className="brand-titles">
          <h1>Statement Categorizer</h1>
          <p className="subtitle">
            Deterministic Tax Engine for Freelancers & Tech Small Businesses
          </p>
        </div>
      </div>

      <div className="header-right">
        <div className="engine-status-pill">
          <span className="pulsing-dot" />
          <span>Deterministic Brain (Zero LLM Calls)</span>
        </div>

        {filename && (
          <div className="action-buttons">
            <button
              type="button"
              className="btn-outline"
              onClick={onReset}
              title="Upload another statement file"
            >
              <Upload size={15} /> Upload New
            </button>
            <button
              type="button"
              className="btn-primary export-btn"
              onClick={onExport}
              disabled={isExportDisabled}
              title="Download accountant-ready CSV with tax breakdown"
            >
              <Download size={15} /> Export Tax CSV
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
