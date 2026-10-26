import React from 'react';

export default function CategoryFilter({
  categories = [],
  activeFilter = 'all',
  onFilterChange,
  needsReviewCount = 0,
  totalCount = 0,
}) {
  const isCustomCategory =
    activeFilter !== 'all' &&
    activeFilter !== 'needs_review' &&
    activeFilter !== 'deductions';

  return (
    <div className="glass-card filter-container-bar">
      <div className="filter-left-pills">
        {/* All Transactions Pill */}
        <button
          type="button"
          className={`glass-filter-pill ${activeFilter === 'all' ? 'pill-active' : ''}`}
          onClick={() => onFilterChange('all')}
        >
          <span>All Records</span>
          <span className="pill-count-tag mono-num">{totalCount}</span>
        </button>

        {/* Needs Review Pill with Amber Highlight */}
        <button
          type="button"
          className={`glass-filter-pill pill-needs-review ${activeFilter === 'needs_review' ? 'pill-review-active' : ''}`}
          onClick={() => onFilterChange('needs_review')}
        >
          <span>Needs Review</span>
          {needsReviewCount > 0 && (
            <span className="pill-count-tag pill-amber-tag mono-num">
              {needsReviewCount}
            </span>
          )}
        </button>

        {/* Deductions Only Pill */}
        <button
          type="button"
          className={`glass-filter-pill ${activeFilter === 'deductions' ? 'pill-active' : ''}`}
          onClick={() => onFilterChange('deductions')}
        >
          <span>Tax Deductible</span>
        </button>
      </div>

      {/* Category Dropdown Filter */}
      <div className="filter-right-category">
        <label htmlFor="tax-category-filter" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
          Category:
        </label>
        <select
          id="tax-category-filter"
          className="glass-dropdown-select"
          value={isCustomCategory ? activeFilter : ''}
          onChange={(e) => {
            const val = e.target.value;
            onFilterChange(val ? val : 'all');
          }}
        >
          <option value="">All Categories ({categories.length})</option>
          {categories.map((catName) => (
            <option key={catName} value={catName}>
              {catName}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
