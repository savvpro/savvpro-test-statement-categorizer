import React from 'react';
import { X, ShieldCheck, Cpu, AlertTriangle, BookOpen } from 'lucide-react';

interface ExplainModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ExplainModal: React.FC<ExplainModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Cpu size={22} color="var(--color-brand)" />
            <h3 className="modal-title">How Categorization Works</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-body">
          <div style={{ padding: '12px 16px', background: 'var(--color-success-bg)', border: '1px solid var(--color-success)', borderRadius: 'var(--radius-md)', marginBottom: '16px', color: '#6ee7b7', display: 'flex', alignItems: 'center', gap: '10px' }}>
            <ShieldCheck size={20} />
            <div>
              <strong>100% Deterministic Engine (Zero External AI Runtime)</strong>
              <div style={{ fontSize: '0.825rem', color: '#a7f3d0' }}>
                Your financial data stays local and private. Categorization is performed solely by transparent, auditable Python heuristics.
              </div>
            </div>
          </div>

          <h4>1. Layered Decision Hierarchy</h4>
          <ul>
            <li>
              <strong>Layer 1: Internal Transfers & Settlements:</strong> Detects movements between accounts (<code>TRANSFER TO SAVINGS</code>, <code>AUTOPAY CREDIT CARD</code>) and marks them <code>Transfer (not spending)</code> to strictly prevent double-counting expenses.
            </li>
            <li>
              <strong>Layer 2: Returns & Refunds:</strong> Identifies <code>REFUND</code>, <code>RETURN</code>, or chargebacks. These offset expenses and are never misclassified as taxable business revenue.
            </li>
            <li>
              <strong>Layer 3: Personal / Owner Draws:</strong> Flags personal purchases (<code>GROCERY OUTLET</code>, <code>NETFLIX</code>) on a business account so they are not deducted.
            </li>
            <li>
              <strong>Layer 4: Inbound Client Revenue:</strong> Verifies positive deposits matching invoice descriptors (<code>CLIENT PAYMENT</code>, <code>INVOICE #</code>, <code>RETAINER</code>) as gross income. Unverified deposits are never assumed to be income.
            </li>
            <li>
              <strong>Layer 5: Exact Merchant Lookup:</strong> High-confidence matching against verified SaaS (Adobe, Figma, GitHub), transit (Uber, Lyft), and vendor dictionaries.
            </li>
            <li>
              <strong>Layer 6: Mangled Descriptors:</strong> Resolves payment processor formats like <code>SQ *ARTISAN BAKERY</code> or <code>ADBE*CREATIVECLOUD</code>.
            </li>
            <li>
              <strong>Layer 7: Needs Review Fallback:</strong> If confidence is low or a merchant is inherently ambiguous (e.g. <code>JOES CAFE 9921</code> or generic <code>AMAZON.COM</code>), the engine safely flags it for user verification rather than guessing incorrectly.
            </li>
          </ul>

          <h4>2. Schedule C Tax Compliance Rules</h4>
          <ul>
            <li>
              <strong>Meals & Coffee:</strong> Flagged for the IRS Schedule C 50% business meal deduction rule (Line 24b). The app displays gross cost and labels the 50% tax limitation.
            </li>
            <li>
              <strong>Transfers:</strong> Excluded from both operating income and operating expenses.
            </li>
            <li>
              <strong>Decimal Precision:</strong> All financial arithmetic uses Python <code>Decimal</code> and fixed-point math to prevent IEEE-754 floating-point rounding errors.
            </li>
          </ul>

          <h4>3. Duplicate Charge Detection</h4>
          <p>
            Identical normalized descriptions and amounts occurring within a 3-day window are highlighted with a duplicate alert chip so freelancers can spot accidental double charges.
          </p>
        </div>
      </div>
    </div>
  );
};
