import React, { useState, useEffect } from 'react';
import { X, Check, AlertTriangle, ShieldAlert, BookmarkCheck, FileText } from 'lucide-react';

export default function ReviewModal({
  transaction,
  allCategories,
  onClose,
  onSave,
}) {
  const [selectedCategory, setSelectedCategory] = useState('');
  const [applyToMerchant, setApplyToMerchant] = useState(false);
  const [notes, setNotes] = useState('');

  useEffect(() => {
    if (transaction) {
      setSelectedCategory(transaction.suggested_category || transaction.category);
      setNotes(transaction.notes || '');
      setApplyToMerchant(false);
    }
  }, [transaction]);

  if (!transaction) return null;

  const formatCurrency = (amt) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(amt || 0);
  };

  const handleSave = () => {
    onSave({
      id: transaction.id,
      category: selectedCategory,
      applyToMerchant,
      merchantPattern: transaction.cleaned_merchant || transaction.raw_description,
      notes: notes.trim() || null,
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="glass-panel modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '100%',
          maxWidth: 540,
          padding: '24px',
          background: 'rgba(16, 21, 33, 0.95)',
          border: '1px solid var(--border-hover)',
        }}
      >
        {/* Modal Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 34,
              height: 34,
              borderRadius: 8,
              background: transaction.needs_review ? 'rgba(245, 158, 11, 0.15)' : 'rgba(99, 102, 241, 0.15)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              {transaction.needs_review ? (
                <AlertTriangle size={18} color="#f59e0b" />
              ) : (
                <BookmarkCheck size={18} color="#818cf8" />
              )}
            </div>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {transaction.needs_review ? 'Resolve Uncertain Row' : 'Edit Row Category'}
              </h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Auditable classification for tax preparation
              </span>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: 4,
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Transaction Summary Card */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '14px 16px',
          marginBottom: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {transaction.raw_description}
            </span>
            <span className="mono-text" style={{ fontSize: '1rem', fontWeight: 700, color: '#34d399' }}>
              {formatCurrency(transaction.amount)}
            </span>
          </div>

          <div style={{ display: 'flex', gap: 10, fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            <span>Date: {transaction.date || '—'}</span>
            <span>•</span>
            <span>Cleaned: {transaction.cleaned_merchant || '—'}</span>
            <span>•</span>
            <span>Confidence: {Math.round(transaction.confidence * 100)}%</span>
          </div>

          {/* Brain Explanation */}
          <div style={{
            marginTop: 6,
            padding: '8px 10px',
            background: 'rgba(99, 102, 241, 0.08)',
            borderRadius: 6,
            border: '1px solid rgba(99, 102, 241, 0.2)',
            fontSize: '0.78rem',
            color: 'var(--text-secondary)',
          }}>
            <strong>Brain Note:</strong> {transaction.reason}
          </div>
        </div>

        {/* Category Picker */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
            Select Tax Category
          </label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            style={{
              width: '100%',
              background: '#111622',
              border: '1px solid var(--border-hover)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              padding: '10px 14px',
              fontSize: '0.88rem',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            {allCategories.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name} ({c.schedule_c_line})
              </option>
            ))}
          </select>
        </div>

        {/* Business Purpose Notes */}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
            Business Purpose / Memo (Optional for IRS Audit Proof)
          </label>
          <input
            type="text"
            placeholder="e.g. Lunch with Acme client to discuss contract renewal"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            style={{
              width: '100%',
              background: '#111622',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-primary)',
              padding: '9px 12px',
              fontSize: '0.82rem',
              outline: 'none',
            }}
          />
        </div>

        {/* Remember Rule Checkbox */}
        {transaction.cleaned_merchant && (
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '10px 12px',
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            cursor: 'pointer',
            marginBottom: 20,
            fontSize: '0.8rem',
            color: 'var(--text-primary)',
          }}>
            <input
              type="checkbox"
              checked={applyToMerchant}
              onChange={(e) => setApplyToMerchant(e.target.checked)}
              style={{ cursor: 'pointer', width: 16, height: 16 }}
            />
            <div>
              <div style={{ fontWeight: 600 }}>
                Remember this rule for future transactions
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Always categorize "{transaction.cleaned_merchant}" as {selectedCategory}
              </div>
            </div>
          </label>
        )}

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 10 }}>
          <button onClick={onClose} className="btn btn-secondary btn-sm">
            Cancel
          </button>
          <button onClick={handleSave} className="btn btn-primary btn-sm" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <Check size={14} />
            <span>Confirm & Recalculate</span>
          </button>
        </div>
      </div>
    </div>
  );
}
