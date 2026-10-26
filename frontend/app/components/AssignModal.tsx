"use client";
import React, { useState } from "react";
import { CloseIcon } from "./Icons";
import { updateTransaction } from "../api";
import { ModalTransaction } from "../types";

interface AssignModalProps {
  isOpen: boolean;
  transaction: ModalTransaction | null;
  statementId: number;
  onClose: () => void;
  onUpdated: (updated?: unknown) => void;
}

const SCHEDULE_C_CATEGORIES = [
  { value: "advertising", label: "Advertising (Line 8)", deductible: "100%" },
  { value: "software_subscriptions", label: "Software & Subscriptions (Line 18)", deductible: "100%" },
  { value: "office_supplies", label: "Office Supplies (Line 18)", deductible: "100%" },
  { value: "travel", label: "Travel & Transport (Line 24a)", deductible: "100%" },
  { value: "meals", label: "Meals & Dining (Line 24b)", deductible: "50% Limit" },
  { value: "vehicle", label: "Vehicle & Mileage (Line 9)", deductible: "100%" },
  { value: "contract_labor", label: "Contract Labor (Line 11)", deductible: "100%" },
  { value: "professional_services", label: "Professional & Legal Services (Line 17)", deductible: "100%" },
  { value: "insurance", label: "Insurance (Line 15)", deductible: "100%" },
  { value: "rent_utilities", label: "Rent & Utilities (Lines 20b, 25)", deductible: "100%" },
  { value: "bank_processing_fees", label: "Bank & Processing Fees (Line 18)", deductible: "100%" },
  { value: "education", label: "Education & Seminars (Line 18)", deductible: "100%" },
  { value: "equipment", label: "Equipment & Hardware (Line 13)", deductible: "100%" },
  { value: "taxes_licenses", label: "Taxes & Licenses (Line 23)", deductible: "100%" },
  { value: "business_income", label: "Business Income (Line 1)", deductible: "N/A" },
  { value: "refund_reimbursement", label: "Refund or Reimbursement", deductible: "N/A" },
  { value: "personal", label: "Personal / Non-Deductible (Exclude)", deductible: "0%" },
  { value: "transfer", label: "Transfer (Exclude)", deductible: "0%" },
  { value: "credit_card_payment", label: "Credit Card Payment (Exclude)", deductible: "0%" },
];

export function AssignModal({
  isOpen,
  transaction,
  statementId,
  onClose,
  onUpdated,
}: AssignModalProps) {
  const [category, setCategory] = useState("office_supplies");
  const [saveRule, setSaveRule] = useState(true);
  const [loading, setLoading] = useState(false);

  React.useEffect(() => {
    if (transaction) {
      const rawCat = (transaction.rawTx?.category || transaction.category || "")
        .toLowerCase()
        .replace(/\s+/g, "_");
      if (rawCat && rawCat !== "needs_review" && SCHEDULE_C_CATEGORIES.some((c) => c.value === rawCat)) {
        setCategory(rawCat);
      } else {
        setCategory("office_supplies");
      }
    }
  }, [transaction]);

  if (!isOpen || !transaction) return null;

  const handleSave = async () => {
    setLoading(true);
    try {
      const sId = transaction.rawTx?.statement_id || statementId;
      if (transaction.id && sId) {
        const res = await updateTransaction(sId, transaction.id, {
          category,
          status: "user_confirmed",
          save_rule: saveRule,
        });
        onUpdated(res);
      } else {
        // Fallback local update
        onUpdated({
          ...transaction,
          category,
          status: "categorized",
        });
      }
      onClose();
    } catch (err) {
      console.error("Update failed:", err);
      // Update local state anyway
      onUpdated({
        ...transaction,
        category,
        status: "categorized",
      });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-box" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">Assign Category</div>
          <button className="modal-close-btn" onClick={onClose}>
            <CloseIcon size={18} />
          </button>
        </div>

        {/* Transaction Summary Card */}
        <div
          style={{
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: 8,
            padding: "12px 16px",
            marginBottom: 20,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, color: "#0f172a" }}>
              {transaction.description}
            </div>
            <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
              {transaction.date}
            </div>
          </div>
          <div
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: transaction.isPositive ? "#16a34a" : "#0f172a",
            }}
          >
            {transaction.amount}
          </div>
        </div>

        {/* Category Selector */}
        <div className="form-group">
          <label className="form-label">Schedule C Category</label>
          <select
            className="form-select"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {SCHEDULE_C_CATEGORIES.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label} ({cat.deductible})
              </option>
            ))}
          </select>
        </div>

        {/* Save as Rule Checkbox */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginTop: 16,
            fontSize: 13,
            color: "#334155",
          }}
        >
          <input
            type="checkbox"
            id="saveRuleCheck"
            checked={saveRule}
            onChange={(e) => setSaveRule(e.target.checked)}
            style={{ width: 16, height: 16, accentColor: "#2563eb", cursor: "pointer" }}
          />
          <label htmlFor="saveRuleCheck" style={{ cursor: "pointer" }}>
            Always categorize <strong>{transaction.description}</strong> this way (creates deterministic rule)
          </label>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose} disabled={loading}>
            Cancel
          </button>
          <button className="btn-primary" onClick={handleSave} disabled={loading}>
            {loading ? "Saving..." : "Save & Categorize"}
          </button>
        </div>
      </div>
    </div>
  );
}
