import React from 'react';
import { CategorySummaryItem } from '../types';
import { PieChart, Filter } from 'lucide-react';

interface CategoryBreakdownProps {
  breakdown: CategorySummaryItem[];
  selectedCategory: string;
  onSelectCategory: (cat: string) => void;
}

export const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({
  breakdown,
  selectedCategory,
  onSelectCategory,
}) => {
  const formatMoney = (val: string | number) => {
    const num = parseFloat(String(val));
    if (isNaN(num)) return '$0.00';
    return `$${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <div className="breakdown-card">
      <div className="breakdown-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <PieChart size={20} color="var(--color-brand)" />
          <h3 className="breakdown-title">Expense & Transaction Category Breakdown</h3>
        </div>
        {selectedCategory && (
          <button
            className="btn btn-outline"
            style={{ padding: '4px 10px', fontSize: '0.75rem' }}
            onClick={() => onSelectCategory('')}
          >
            Clear Filter ({selectedCategory})
          </button>
        )}
      </div>

      <div className="breakdown-grid">
        {breakdown.map((item) => {
          const isSelected = selectedCategory === item.category;
          return (
            <div
              key={item.category}
              className={`category-row-item ${isSelected ? 'active' : ''}`}
              style={{
                borderColor: isSelected ? 'var(--color-brand)' : undefined,
                background: isSelected ? 'rgba(59, 130, 246, 0.12)' : undefined,
              }}
              onClick={() => onSelectCategory(isSelected ? '' : item.category)}
            >
              <div className="cat-top">
                <span className="cat-name">{item.category}</span>
                <span className="cat-amount">{formatMoney(item.total_amount)}</span>
              </div>

              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{
                    width: `${Math.min(item.percentage, 100)}%`,
                    backgroundColor:
                      item.category === 'Needs Review'
                        ? 'var(--color-warning)'
                        : item.category === 'Income'
                        ? 'var(--color-success)'
                        : item.category === 'Refund'
                        ? '#38bdf8'
                        : item.category === 'Transfer (not spending)'
                        ? '#94a3b8'
                        : 'var(--color-brand)',
                  }}
                />
              </div>

              <div className="cat-bottom">
                <span>
                  {item.count} transaction{item.count !== 1 ? 's' : ''}
                  {item.percentage > 0 ? ` (${item.percentage}%)` : ''}
                </span>
                {item.deductible_note && (
                  <span className="tax-badge" title={item.deductible_note}>
                    {item.category === 'Meals & Coffee' ? '50% Deductible' : 'Schedule C'}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
