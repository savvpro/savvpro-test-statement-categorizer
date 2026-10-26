import React, { useState, useMemo } from 'react';
import { Transaction } from '../types';
import {
  Search,
  Filter,
  Download,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Edit2,
  FileSpreadsheet,
} from 'lucide-react';

interface TransactionTableProps {
  transactions: Transaction[];
  categories: string[];
  selectedCategory: string;
  onSelectCategory: (cat: string) => void;
  onUpdateCategory: (txnId: string, newCategory: string) => void;
  onExportCsv: () => void;
  isExporting: boolean;
}

export const TransactionTable: React.FC<TransactionTableProps> = ({
  transactions,
  categories,
  selectedCategory,
  onSelectCategory,
  onUpdateCategory,
  onExportCsv,
  isExporting,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [onlyNeedsReview, setOnlyNeedsReview] = useState(false);
  const [onlyDuplicates, setOnlyDuplicates] = useState(false);
  const [sortField, setSortField] = useState<'date' | 'amount'>('date');
  const [sortAsc, setSortAsc] = useState(false);

  // Filter and sort transactions
  const filteredTransactions = useMemo(() => {
    return transactions
      .filter((tx) => {
        // Category filter
        if (selectedCategory && tx.category !== selectedCategory) {
          return false;
        }
        // Only Needs Review filter
        if (onlyNeedsReview && !tx.needs_review && tx.category !== 'Needs Review') {
          return false;
        }
        // Only Duplicates filter
        if (onlyDuplicates && !tx.is_duplicate) {
          return false;
        }
        // Search filter
        if (searchTerm.trim()) {
          const q = searchTerm.toLowerCase();
          const matchDesc = tx.description.toLowerCase().includes(q);
          const matchCat = tx.category.toLowerCase().includes(q);
          const matchReason = tx.reason.toLowerCase().includes(q);
          if (!matchDesc && !matchCat && !matchReason) {
            return false;
          }
        }
        return true;
      })
      .sort((a, b) => {
        if (sortField === 'date') {
          const comp = a.date.localeCompare(b.date);
          return sortAsc ? comp : -comp;
        } else {
          const amtA = parseFloat(a.amount);
          const amtB = parseFloat(b.amount);
          return sortAsc ? amtA - amtB : amtB - amtA;
        }
      });
  }, [transactions, selectedCategory, onlyNeedsReview, onlyDuplicates, searchTerm, sortField, sortAsc]);

  const formatMoney = (val: string, direction: string) => {
    const num = parseFloat(val);
    const absStr = Math.abs(num).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    if (num < 0) {
      return `-$${absStr}`;
    } else if (num > 0) {
      return `+$${absStr}`;
    }
    return `$${absStr}`;
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.9) {
      return <span className="badge badge-confidence-high">{Math.round(confidence * 100)}% High</span>;
    }
    if (confidence >= 0.7) {
      return <span className="badge badge-confidence-mid">{Math.round(confidence * 100)}% Med</span>;
    }
    return <span className="badge badge-confidence-low">{Math.round(confidence * 100)}% Low</span>;
  };

  return (
    <div>
      {/* Filter and action toolbar */}
      <div className="filter-bar">
        <div className="filter-left">
          {/* Search box */}
          <div className="search-input-wrapper">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              className="search-input"
              placeholder="Search merchant, description, reason..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          {/* Category Dropdown Filter */}
          <select
            className="select-filter"
            value={selectedCategory}
            onChange={(e) => onSelectCategory(e.target.value)}
          >
            <option value="">All Categories ({transactions.length})</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>

          {/* Quick toggle: Needs Review */}
          <button
            className={`btn ${onlyNeedsReview ? 'btn-primary' : 'btn-outline'}`}
            style={{ fontSize: '0.8rem', padding: '7px 12px' }}
            onClick={() => setOnlyNeedsReview(!onlyNeedsReview)}
          >
            <HelpCircle size={14} />
            <span>Needs Review</span>
          </button>

          {/* Quick toggle: Duplicates */}
          <button
            className={`btn ${onlyDuplicates ? 'btn-primary' : 'btn-outline'}`}
            style={{ fontSize: '0.8rem', padding: '7px 12px' }}
            onClick={() => setOnlyDuplicates(!onlyDuplicates)}
          >
            <AlertTriangle size={14} />
            <span>Duplicates</span>
          </button>

          {(searchTerm || selectedCategory || onlyNeedsReview || onlyDuplicates) && (
            <button
              className="btn btn-outline"
              style={{ fontSize: '0.8rem', padding: '7px 10px' }}
              onClick={() => {
                setSearchTerm('');
                onSelectCategory('');
                setOnlyNeedsReview(false);
                setOnlyDuplicates(false);
              }}
            >
              Reset Filters
            </button>
          )}
        </div>

        {/* Export CSV button */}
        <button
          className="btn btn-success"
          onClick={onExportCsv}
          disabled={isExporting || transactions.length === 0}
          title="Download the reviewed statement CSV including all manual category edits"
        >
          <Download size={16} />
          <span>{isExporting ? 'Exporting...' : 'Export Reviewed CSV'}</span>
        </button>
      </div>

      {/* Table container */}
      <div className="table-container">
        <table className="transactions-table">
          <thead>
            <tr>
              <th
                className="col-date"
                style={{ cursor: 'pointer', userSelect: 'none' }}
                onClick={() => {
                  if (sortField === 'date') setSortAsc(!sortAsc);
                  else {
                    setSortField('date');
                    setSortAsc(false);
                  }
                }}
              >
                Date {sortField === 'date' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th className="col-desc">Description / Merchant</th>
              <th
                className="col-amount"
                style={{ cursor: 'pointer', userSelect: 'none' }}
                onClick={() => {
                  if (sortField === 'amount') setSortAsc(!sortAsc);
                  else {
                    setSortField('amount');
                    setSortAsc(false);
                  }
                }}
              >
                Amount {sortField === 'amount' ? (sortAsc ? '▲' : '▼') : ''}
              </th>
              <th className="col-category">Assigned Category (Schedule C)</th>
              <th className="col-confidence">Confidence</th>
              <th className="col-reason">Engine Decision & Reason</th>
              <th className="col-status">Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredTransactions.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  No transactions match the selected filter criteria.
                </td>
              </tr>
            ) : (
              filteredTransactions.map((tx) => {
                const isNeedsReview = tx.needs_review || tx.category === 'Needs Review';
                const isExpense = tx.direction === 'expense';
                const isIncome = tx.direction === 'income';
                const isTransfer = tx.direction === 'transfer';
                const isRefund = tx.direction === 'refund';

                let amountColorClass = '';
                if (isExpense) amountColorClass = 'amount-expense';
                else if (isIncome) amountColorClass = 'amount-income';
                else if (isTransfer) amountColorClass = 'amount-transfer';
                else if (isRefund) amountColorClass = 'amount-refund';

                return (
                  <tr key={tx.id} className={isNeedsReview ? 'row-needs-review' : ''}>
                    {/* Date */}
                    <td className="col-date" style={{ color: 'var(--text-secondary)' }}>
                      {tx.date}
                    </td>

                    {/* Description */}
                    <td className="col-desc">
                      <div style={{ fontWeight: 500, color: '#f8fafc' }}>
                        {tx.description}
                      </div>
                      {tx.is_duplicate && (
                        <div style={{ marginTop: '4px' }}>
                          <span className="badge badge-duplicate" title={tx.duplicate_reason || ''}>
                            <AlertTriangle size={12} /> {tx.duplicate_reason}
                          </span>
                        </div>
                      )}
                    </td>

                    {/* Amount */}
                    <td className={`col-amount ${amountColorClass}`}>
                      {formatMoney(tx.amount, tx.direction)}
                    </td>

                    {/* Category Selector */}
                    <td className="col-category">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <select
                          className={`category-select-inline ${tx.user_edited ? 'edited' : ''}`}
                          value={tx.category}
                          onChange={(e) => onUpdateCategory(tx.id, e.target.value)}
                        >
                          {categories.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                        {tx.user_edited && (
                          <span title="Manually edited by user" style={{ color: 'var(--color-brand)' }}>
                            <Edit2 size={13} />
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Confidence */}
                    <td className="col-confidence">
                      {getConfidenceBadge(tx.confidence)}
                    </td>

                    {/* Reason */}
                    <td className="col-reason">
                      <div className="reason-text">
                        {tx.reason}
                      </div>
                    </td>

                    {/* Status */}
                    <td className="col-status">
                      {isNeedsReview ? (
                        <span className="badge badge-review">
                          <HelpCircle size={12} /> Needs Review
                        </span>
                      ) : (
                        <span style={{ color: 'var(--color-success)', fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                          <CheckCircle size={13} /> Categorized
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
