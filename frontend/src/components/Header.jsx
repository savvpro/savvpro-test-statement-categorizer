import React from 'react';
import { Cpu, ShieldCheck, Sparkles, FileSpreadsheet, Download } from 'lucide-react';

export default function Header({ onExportClick, transactionCount, needsReviewCount }) {
  return (
    <header style={{
      borderBottom: '1px solid var(--border-subtle)',
      background: 'rgba(8, 10, 15, 0.85)',
      backdropFilter: 'blur(16px)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      padding: '16px 24px',
    }}>
      <div style={{
        maxWidth: 1400,
        margin: '0 auto',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16,
      }}>
        {/* Logo & Persona Info */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: 12,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 20px rgba(99, 102, 241, 0.4)',
          }}>
            <Cpu size={24} color="#fff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <h1 style={{ fontSize: '1.25rem', fontWeight: 800, letterSpacing: '-0.02em' }}>
                TaxBrain
              </h1>
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                background: 'rgba(99, 102, 241, 0.15)',
                color: '#818cf8',
                padding: '2px 8px',
                borderRadius: 6,
                border: '1px solid rgba(99, 102, 241, 0.3)',
              }}>
                IRS Schedule C Engine
              </span>
            </div>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
              Autonomous Statement Categorizer for Freelancers & Solo-Proprietors
            </p>
          </div>
        </div>

        {/* Right Badges & Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Zero-LLM Brain Assurance Badge */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 12px',
            background: 'rgba(16, 185, 129, 0.1)',
            border: '1px solid rgba(16, 185, 129, 0.25)',
            borderRadius: 8,
            fontSize: '0.75rem',
            color: '#34d399',
            fontWeight: 600,
          }}>
            <ShieldCheck size={16} />
            <span>Deterministic Brain (Zero LLM / 100% Auditable)</span>
          </div>

          {transactionCount > 0 && (
            <button
              onClick={onExportClick}
              className="btn btn-secondary btn-sm"
              style={{ display: 'flex', alignItems: 'center', gap: 6 }}
            >
              <Download size={15} />
              <span>Export Tax Summary</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
