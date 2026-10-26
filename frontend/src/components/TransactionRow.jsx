import React from 'react';

export default function TransactionRow({
  transaction,
  categories = {},
  onUpdate,
  isExpanded,
  onToggleExpand,
}) {
  const {
    id,
    date,
    raw_description,
    clean_merchant,
    amount,
    direction,
    category,
    schedule_c_line,
    deductible_percentage,
    deductible_amount,
    confidence,
    status,
    needs_review,
    review_reason,
    decision_rule,
  } = transaction;

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(val || 0);
  };

  const getAmountColor = () => {
    switch (direction) {
      case 'INFLOW':
        return 'var(--accent-green)';
      case 'REFUND':
        return '#0284c7';
      case 'TRANSFER':
        return 'var(--text-muted)';
      default:
        return 'var(--text-main)';
    }
  };

  const getStatusPill = () => {
    if (status === 'AUTO_VERIFIED') {
      return <span className="pill-badge pill-green">Verified</span>;
    }
    if (status === 'MANUALLY_APPROVED') {
      return <span className="pill-badge pill-purple">Approved</span>;
    }
    if (status === 'PERSONAL') {
      return <span className="pill-badge" style={{ background: 'var(--accent-red-soft)', color: 'var(--accent-red)' }}>Personal</span>;
    }
    return <span className="pill-badge pill-amber">Needs Review</span>;
  };

  const getConfidencePill = () => {
    const pct = Math.round((confidence || 0) * 100);
    if (pct >= 85) {
      return <span className="pill-badge pill-green mono-num">{pct}%</span>;
    }
    if (pct >= 50) {
      return <span className="pill-badge pill-amber mono-num">{pct}%</span>;
    }
    return <span className="pill-badge pill-slate mono-num">{pct}%</span>;
  };

  const handleCategorySelect = (e) => {
    const newCategory = e.target.value;
    const catInfo = categories[newCategory] || {
      schedule_c_line: 'Pending',
      tax_deductible: false,
      deductible_percentage: 0.0,
    };

    const isDeductible = catInfo.tax_deductible && direction === 'OUTFLOW';
    const newDeductibleAmt = isDeductible
      ? Math.round((amount * catInfo.deductible_percentage) * 100) / 100
      : 0.0;

    onUpdate({
      ...transaction,
      category: newCategory,
      schedule_c_line: catInfo.schedule_c_line,
      tax_deductible: isDeductible,
      deductible_percentage: catInfo.deductible_percentage,
      deductible_amount: newDeductibleAmt,
      needs_review: false,
      status: 'MANUALLY_APPROVED',
    });
  };

  const handleQuickApprove = (e) => {
    e.stopPropagation();
    const catInfo = categories[category] || {
      schedule_c_line: schedule_c_line || 'Pending',
      tax_deductible: true,
      deductible_percentage: deductible_percentage || 1.0,
    };

    const isDeductible = catInfo.tax_deductible && direction === 'OUTFLOW';
    const newDeductibleAmt = isDeductible
      ? Math.round((amount * catInfo.deductible_percentage) * 100) / 100
      : 0.0;

    onUpdate({
      ...transaction,
      needs_review: false,
      status: 'MANUALLY_APPROVED',
      tax_deductible: isDeductible,
      deductible_amount: newDeductibleAmt,
    });
  };

  // Avatar initials
  const initials = (clean_merchant || 'TX').slice(0, 2).toUpperCase();

  return (
    <>
      <tr
        className={`frosted-row ${needs_review ? 'row-flagged-amber' : ''}`}
        onClick={onToggleExpand}
        style={{ cursor: 'pointer' }}
      >
        <td className="mono-num" style={{ whiteSpace: 'nowrap', fontSize: '12px', color: 'var(--text-muted)' }}>
          {date}
        </td>

        <td>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'rgba(241, 245, 249, 0.9)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '11px',
                color: 'var(--accent-purple)',
                border: '1px solid var(--glass-border)',
              }}
            >
              {initials}
            </div>
            <div>
              <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>{clean_merchant}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{id}</div>
            </div>
          </div>
        </td>

        <td className="mono-num">
          <span style={{ fontWeight: 700, color: getAmountColor() }}>
            {direction === 'OUTFLOW' ? '-' : '+'}
            {formatCurrency(amount)}
          </span>
        </td>

        <td>
          <span className="pill-badge pill-slate" style={{ fontSize: '10px' }}>
            {direction}
          </span>
        </td>

        <td onClick={(e) => needs_review && e.stopPropagation()}>
          {needs_review ? (
            <select
              className="clean-select"
              value={category}
              onChange={handleCategorySelect}
              aria-label={`Assign category for ${clean_merchant}`}
            >
              {Object.keys(categories).map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '7px' }}>
              <span
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: categories[category]?.color || '#8b5cf6',
                }}
              />
              <span style={{ fontWeight: 600, color: 'var(--text-sub)' }}>{category}</span>
            </div>
          )}
        </td>

        <td>{getConfidencePill()}</td>

        <td>{getStatusPill()}</td>

        <td style={{ textAlign: 'right' }} onClick={(e) => e.stopPropagation()}>
          {needs_review ? (
            <button
              type="button"
              className="btn-pill-primary"
              style={{ padding: '4px 12px', fontSize: '11px' }}
              onClick={handleQuickApprove}
            >
              Approve
            </button>
          ) : (
            <button
              type="button"
              className="btn-pill-glass"
              style={{ padding: '4px 10px', fontSize: '11px' }}
              onClick={onToggleExpand}
            >
              {isExpanded ? 'Less' : 'Details'}
            </button>
          )}
        </td>
      </tr>

      {/* Expanded Audit Card */}
      {isExpanded && (
        <tr>
          <td colSpan="8" style={{ background: 'rgba(255, 255, 255, 0.95)', padding: '16px 20px', borderBottom: '1px solid rgba(226, 232, 240, 0.8)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '14px', fontSize: '12px' }}>
              <div>
                <strong style={{ display: 'block', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase' }}>
                  Raw Bank Description
                </strong>
                <span className="mono-num" style={{ color: 'var(--text-main)' }}>{raw_description}</span>
              </div>

              <div>
                <strong style={{ display: 'block', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase' }}>
                  Schedule C Tax Line
                </strong>
                <span style={{ fontWeight: 600, color: 'var(--accent-purple)' }}>{schedule_c_line || 'N/A'}</span>
              </div>

              <div>
                <strong style={{ display: 'block', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase' }}>
                  Deductible Portion
                </strong>
                <span style={{ fontWeight: 600 }}>
                  {Math.round((deductible_percentage || 0) * 100)}% ({formatCurrency(deductible_amount)})
                </span>
              </div>

              <div>
                <strong style={{ display: 'block', color: 'var(--text-muted)', fontSize: '11px', textTransform: 'uppercase' }}>
                  Decision Rule
                </strong>
                <span style={{ color: 'var(--text-sub)' }}>{decision_rule || 'Deterministic rule'}</span>
              </div>

              {review_reason && (
                <div style={{ gridColumn: '1 / -1', background: 'var(--accent-amber-soft)', padding: '8px 12px', borderRadius: '8px' }}>
                  <strong style={{ color: 'var(--accent-amber)', fontSize: '11px', textTransform: 'uppercase' }}>
                    Review Flag Reason
                  </strong>
                  <div style={{ color: 'var(--accent-amber)', fontWeight: 500 }}>{review_reason}</div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
