import React from 'react';

const CATEGORIES = [
  'ALL',
  'Software',
  'Travel',
  'Meals',
  'Office Supplies',
  'Income',
  'Refund',
  'Transfer',
  'Other Business Expense',
  'Needs Review',
];

export default function FilterBar({
  searchQuery,
  setSearchQuery,
  selectedCategory,
  setSelectedCategory,
  selectedStatus,
  setSelectedStatus,
  needsReviewCount,
  totalCount,
  filteredCount,
}) {
  return (
    <div className="filter-bar">
      <div className="filter-group">
        <input
          type="text"
          className="input-search"
          placeholder="Search by merchant, description, or date..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        <select
          className="select-filter"
          value={selectedCategory}
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          {CATEGORIES.map((cat) => (
            <option key={cat} value={cat}>
              {cat === 'ALL' ? 'All Categories' : cat}
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <div className="tabs-filter">
          <button
            type="button"
            className={`tab-btn ${selectedStatus === 'ALL' ? 'active' : ''}`}
            onClick={() => setSelectedStatus('ALL')}
          >
            All ({totalCount})
          </button>
          <button
            type="button"
            className={`tab-btn ${selectedStatus === 'needs_review' ? 'active' : ''}`}
            onClick={() => setSelectedStatus('needs_review')}
            style={needsReviewCount > 0 ? { color: 'var(--warning)', fontWeight: 600 } : {}}
          >
            Needs Review ({needsReviewCount})
          </button>
          <button
            type="button"
            className={`tab-btn ${selectedStatus === 'categorized' ? 'active' : ''}`}
            onClick={() => setSelectedStatus('categorized')}
          >
            Auto-Categorized
          </button>
          <button
            type="button"
            className={`tab-btn ${selectedStatus === 'manual' ? 'active' : ''}`}
            onClick={() => setSelectedStatus('manual')}
          >
            User-Reviewed
          </button>
        </div>

        {(searchQuery || selectedCategory !== 'ALL' || selectedStatus !== 'ALL') && (
          <button
            type="button"
            className="btn btn-outline"
            style={{ padding: '0.35rem 0.65rem', fontSize: '0.75rem' }}
            onClick={() => {
              setSearchQuery('');
              setSelectedCategory('ALL');
              setSelectedStatus('ALL');
            }}
          >
            Reset Filters ({filteredCount})
          </button>
        )}
      </div>
    </div>
  );
}
