"use client";

import { ArrowRightIcon, CheckCircleIcon, ChevronRightIcon, DocumentIcon } from "./Icons";
import { SummaryData } from "../types";

interface TaxReadinessProps {
  summary: SummaryData | null;
  onResolveUnassigned: () => void;
}

export function TaxReadiness({ summary, onResolveUnassigned }: TaxReadinessProps) {
  const total = summary?.status_counts?.total ?? 0;
  const needsReview = summary?.status_counts?.needs_review ?? 0;
  const verified = Math.max(0, total - needsReview);
  const readinessPct = total > 0 ? Math.round((verified / total) * 100) : 0;

  // Donut SVG circumference calculation
  const radius = 26;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (readinessPct / 100) * circumference;


  return (
    <div className="right-col">
      {/* Tax Readiness Card */}
      <div className="card tax-readiness-card">
        <div className="readiness-header">
          <span className="card-title">Tax Readiness</span>
          <span className="stage-badge">Stage 2 of 4</span>
        </div>

        <div className="readiness-body">
          {/* Circular Donut Ring */}
          <div className="donut-wrap">
            <svg width="64" height="64">
              <circle
                cx="32"
                cy="32"
                r={radius}
                fill="none"
                stroke="#e2e8f0"
                strokeWidth="5"
              />
              <circle
                cx="32"
                cy="32"
                r={radius}
                fill="none"
                stroke="#2563eb"
                strokeWidth="5"
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
              />
            </svg>
            <div className="donut-text">{readinessPct}%</div>
          </div>

          <div className="readiness-info">
            <span className="readiness-title">Documents Ready for Filing</span>
            <p className="readiness-subtext">
              {verified} of {total} transactions verified and cross-referenced with
              your imported receipts.
            </p>
          </div>
        </div>

        {/* Checklist */}
        <div className="readiness-checklist">
          <div className="checklist-item success">
            <div className="check-left">
              <CheckCircleIcon size={16} />
              <span>Bank Feeds Connected</span>
            </div>
            <span style={{ fontWeight: 600, fontSize: 11.5 }}>Complete</span>
          </div>

          <div className="checklist-item pending">
            <div className="check-left">
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  backgroundColor: "#f59e0b",
                }}
              />
              <span>{needsReview} Unassigned Expenses</span>
            </div>
            <button
              className="check-action-link"
              onClick={onResolveUnassigned}
              style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
            >
              <span>Resolve</span>
              <ArrowRightIcon size={12} />
            </button>
          </div>
        </div>
      </div>

      {/* Deduction Safeguard Card */}
      <div className="card safeguard-card">
        <div className="safeguard-thumb">
          <DocumentIcon size={24} />
        </div>
        <div className="safeguard-content">
          <div className="safeguard-title">Deduction Safeguard</div>
          <p className="safeguard-desc">
            Automatic detection for potential home office, mileage, and utility write-offs.
          </p>
        </div>
        <button
          className="safeguard-btn"
          style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
        >
          <span>Configure</span>
          <ChevronRightIcon size={12} />
        </button>
      </div>
    </div>
  );
}
