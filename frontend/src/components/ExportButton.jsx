import React from 'react';

export default function ExportButton({ transactions = [], defaultFilename = 'categorized_statement.csv' }) {
  const handleExport = () => {
    if (!transactions || transactions.length === 0) return;

    const headers = [
      'Date',
      'Raw Description',
      'Clean Merchant',
      'Amount',
      'Direction',
      'Category',
      'Tax Deductible',
      'Deductible %',
      'Deductible Amount',
      'Confidence',
      'Status',
      'Schedule C Line',
      'Review Reason',
    ];

    const escapeCsv = (str) => {
      if (str === null || str === undefined) return '""';
      const s = String(str).replace(/"/g, '""');
      return `"${s}"`;
    };

    const rows = transactions.map((t) => [
      escapeCsv(t.date),
      escapeCsv(t.raw_description),
      escapeCsv(t.clean_merchant),
      t.amount,
      escapeCsv(t.direction),
      escapeCsv(t.category),
      t.tax_deductible ? 'YES' : 'NO',
      `${Math.round((t.deductible_percentage || 0) * 100)}%`,
      t.deductible_amount || 0.0,
      `${Math.round((t.confidence || 0) * 100)}%`,
      escapeCsv(t.status),
      escapeCsv(t.schedule_c_line),
      escapeCsv(t.review_reason || ''),
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((r) => r.join(',')),
    ].join('\r\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', defaultFilename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <button
      type="button"
      className="btn btn-primary"
      onClick={handleExport}
      title="Download complete categorized tax ledger as CSV"
    >
      <svg
        width="15"
        height="15"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <polyline points="7 10 12 15 17 10" />
        <line x1="12" y1="15" x2="12" y2="3" />
      </svg>
      Export Categorized CSV
    </button>
  );
}
