import React, { useState, useMemo } from "react";
import type { CategorizedTransaction } from "../types";
import {
  Search,
  Filter,
  CheckCircle,
  AlertCircle,
  RotateCcw,
  Copy,
  UserCheck,
  HelpCircle,
  Sparkles,
} from "lucide-react";

interface TransactionTableProps {
  transactions: CategorizedTransaction[];
  categories: string[];
  onCategoryChange: (
    transactionId: string,
    newCategory: string,
    saveAsRule: boolean,
    normalizedDesc: string
  ) => void;
  activeFilterCategory: string | null;
  onClearCategoryFilter: () => void;
}

export const TransactionTable: React.FC<TransactionTableProps> = ({
  transactions,
  categories,
  onCategoryChange,
  activeFilterCategory,
  onClearCategoryFilter,
}) => {
  const [activeTab, setActiveTab] = useState<"ALL" | "NEEDS_REVIEW" | "DUPLICATES" | "REFUNDS" | "TRANSFERS">("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [ruleModalTx, setRuleModalTx] = useState<CategorizedTransaction | null>(null);
  const [pendingCategory, setPendingCategory] = useState<string>("");
  const [saveAsRule, setSaveAsRule] = useState<boolean>(true);

  // Filtered transactions
  const filteredList = useMemo(() => {
    return transactions.filter((tx) => {
      // Tab filter
      if (activeTab === "NEEDS_REVIEW" && !tx.needs_review) return false;
      if (activeTab === "DUPLICATES" && !tx.is_duplicate) return false;
      if (activeTab === "REFUNDS" && !tx.is_refund) return false;
      if (activeTab === "TRANSFERS" && !tx.is_transfer) return false;

      // Category filter
      if (activeFilterCategory && tx.category !== activeFilterCategory) return false;

      // Search query filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesDesc = tx.raw_description.toLowerCase().includes(query);
        const matchesNorm = tx.normalized_description.toLowerCase().includes(query);
        const matchesCat = tx.category.toLowerCase().includes(query);
        const matchesReason = tx.reason.toLowerCase().includes(query);
        if (!matchesDesc && !matchesNorm && !matchesCat && !matchesReason) return false;
      }

      return true;
    });
  }, [transactions, activeTab, activeFilterCategory, searchQuery]);

  const handleSelectChange = (tx: CategorizedTransaction, newCat: string) => {
    if (newCat === tx.category) return;
    setRuleModalTx(tx);
    setPendingCategory(newCat);
    setSaveAsRule(true);
  };

  const confirmCategoryChange = () => {
    if (ruleModalTx && pendingCategory) {
      onCategoryChange(
        ruleModalTx.id,
        pendingCategory,
        saveAsRule,
        ruleModalTx.normalized_description
      );
      setRuleModalTx(null);
      setPendingCategory("");
    }
  };

  const cancelCategoryChange = () => {
    setRuleModalTx(null);
    setPendingCategory("");
  };

  const needsReviewCount = transactions.filter((t) => t.needs_review).length;
  const duplicatesCount = transactions.filter((t) => t.is_duplicate).length;
  const refundsCount = transactions.filter((t) => t.is_refund).length;
  const transfersCount = transactions.filter((t) => t.is_transfer).length;

  return (
    <div className="table-wrapper-card">
      {/* Controls & Filter Bar */}
      <div className="table-controls">
        <div className="filter-tabs">
          <button
            type="button"
            className={`tab-btn ${activeTab === "ALL" && !activeFilterCategory ? "active" : ""}`}
            onClick={() => {
              setActiveTab("ALL");
              onClearCategoryFilter();
            }}
          >
            All Transactions ({transactions.length})
          </button>
          <button
            type="button"
            className={`tab-btn review-tab ${activeTab === "NEEDS_REVIEW" ? "active" : ""}`}
            onClick={() => {
              setActiveTab("NEEDS_REVIEW");
              onClearCategoryFilter();
            }}
          >
            <AlertCircle size={14} /> Needs Review ({needsReviewCount})
          </button>
          {duplicatesCount > 0 && (
            <button
              type="button"
              className={`tab-btn duplicate-tab ${activeTab === "DUPLICATES" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("DUPLICATES");
                onClearCategoryFilter();
              }}
            >
              <Copy size={14} /> Duplicates ({duplicatesCount})
            </button>
          )}
          {refundsCount > 0 && (
            <button
              type="button"
              className={`tab-btn refund-tab ${activeTab === "REFUNDS" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("REFUNDS");
                onClearCategoryFilter();
              }}
            >
              <RotateCcw size={14} /> Refunds ({refundsCount})
            </button>
          )}
          {transfersCount > 0 && (
            <button
              type="button"
              className={`tab-btn transfer-tab ${activeTab === "TRANSFERS" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("TRANSFERS");
                onClearCategoryFilter();
              }}
            >
              Transfers ({transfersCount})
            </button>
          )}
        </div>

        <div className="search-and-active-filter">
          {activeFilterCategory && (
            <div className="active-cat-pill">
              <span>Category: <strong>{activeFilterCategory}</strong></span>
              <button type="button" onClick={onClearCategoryFilter}>×</button>
            </div>
          )}
          <div className="search-box">
            <Search size={15} className="search-icon" />
            <input
              type="text"
              placeholder="Filter by merchant or reason..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                className="clear-search"
                onClick={() => setSearchQuery("")}
              >
                ×
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Transactions Table */}
      <div className="table-responsive">
        <table className="transactions-table">
          <thead>
            <tr>
              <th style={{ width: "50px" }}>#</th>
              <th style={{ width: "105px" }}>Date</th>
              <th>Description & Clean Merchant</th>
              <th style={{ width: "115px", textAlign: "right" }}>Amount</th>
              <th style={{ width: "230px" }}>Assigned Category</th>
              <th style={{ width: "110px", textAlign: "center" }}>Confidence</th>
              <th>Rule & Decision Reason</th>
            </tr>
          </thead>
          <tbody>
            {filteredList.length === 0 ? (
              <tr>
                <td colSpan={7} className="empty-table-cell">
                  <div className="empty-table-state">
                    <Filter size={32} />
                    <p>No transactions match the selected filter criteria.</p>
                  </div>
                </td>
              </tr>
            ) : (
              filteredList.map((tx) => {
                const confPercent = Math.round(tx.confidence * 100);
                const isHighConf = tx.confidence >= 0.9;
                const isMedConf = tx.confidence >= 0.75 && tx.confidence < 0.9;

                return (
                  <tr
                    key={tx.id}
                    className={`tx-row ${tx.needs_review ? "row-needs-review" : ""} ${
                      tx.is_duplicate ? "row-duplicate" : ""
                    }`}
                  >
                    <td className="cell-num">{tx.line_number}</td>
                    <td className="cell-date">{tx.date}</td>
                    <td className="cell-desc">
                      <div className="raw-desc-text">{tx.raw_description}</div>
                      <div className="clean-merchant-pill">
                        <Sparkles size={11} />
                        <span>{tx.normalized_description || "RAW"}</span>
                      </div>
                      <div className="badge-row">
                        {tx.is_duplicate && (
                          <span className="edge-badge badge-dup">
                            <Copy size={11} /> Duplicate Charge
                          </span>
                        )}
                        {tx.is_refund && (
                          <span className="edge-badge badge-ref">
                            <RotateCcw size={11} /> Refund Offset (Non-Income)
                          </span>
                        )}
                        {tx.is_transfer && (
                          <span className="edge-badge badge-trans">
                            Non-Spending Transfer
                          </span>
                        )}
                        {tx.is_personal_ambiguous && (
                          <span className="edge-badge badge-ambig">
                            <HelpCircle size={11} /> Personal / Business Check
                          </span>
                        )}
                        {tx.user_overridden && (
                          <span className="edge-badge badge-override">
                            <UserCheck size={11} /> User Saved Rule
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="cell-amount">
                      <span
                        className={`amount-text ${
                          tx.transaction_type === "CREDIT"
                            ? tx.is_refund
                              ? "amt-refund"
                              : "amt-credit"
                            : "amt-debit"
                        }`}
                      >
                        {tx.transaction_type === "CREDIT" ? "+" : "-"}$
                        {tx.amount.toFixed(2)}
                      </span>
                    </td>
                    <td className="cell-category">
                      <select
                        className={`category-select ${
                          tx.category === "Needs Review" ? "select-needs-review" : ""
                        }`}
                        value={tx.category}
                        onChange={(e) => handleSelectChange(tx, e.target.value)}
                      >
                        {categories.map((cat) => (
                          <option key={cat} value={cat}>
                            {cat}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="cell-confidence">
                      <div
                        className={`conf-pill ${
                          isHighConf ? "conf-high" : isMedConf ? "conf-med" : "conf-low"
                        }`}
                      >
                        {confPercent}%
                      </div>
                    </td>
                    <td className="cell-reason">
                      <div className="reason-text">
                        {tx.needs_review && (
                          <AlertCircle size={13} className="reason-alert-icon" />
                        )}
                        <span>{tx.reason}</span>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Confirmation & Save As Rule Modal */}
      {ruleModalTx && (
        <div className="modal-backdrop">
          <div className="modal-dialog">
            <div className="modal-header">
              <Sparkles size={20} className="modal-icon" />
              <h4>Update Category & Remember Rule</h4>
            </div>
            <div className="modal-body">
              <p>
                Change category for <strong>{ruleModalTx.raw_description}</strong> to{" "}
                <span className="highlight-cat">{pendingCategory}</span>?
              </p>
              <div className="rule-checkbox-wrap">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={saveAsRule}
                    onChange={(e) => setSaveAsRule(e.target.checked)}
                  />
                  <span>
                    Save as persistent rule for future statements matching{" "}
                    <strong>"{ruleModalTx.normalized_description}"</strong>
                  </span>
                </label>
              </div>
            </div>
            <div className="modal-footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={cancelCategoryChange}
              >
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={confirmCategoryChange}
              >
                <CheckCircle size={16} /> Confirm & Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
