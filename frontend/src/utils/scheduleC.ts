const SCHEDULE_C_LINES: Record<string, { line: string; hint?: string }> = {
  'Software & Subscriptions': { line: 'Line 18 · Office Exp', hint: 'SaaS & tools' },
  'Travel & Transportation': { line: 'Line 24a · Travel', hint: 'Client travel' },
  'Meals & Entertainment': { line: 'Line 24b · Meals', hint: '50% deductible' },
  'Office Supplies': { line: 'Line 18 · Supplies', hint: 'Office' },
  'Professional Services': { line: 'Line 17 · Legal', hint: 'Contractors' },
  'Marketing & Advertising': { line: 'Line 8 · Advertising', hint: 'Ads' },
  'Equipment & Hardware': { line: 'Line 13 · Equipment', hint: 'Cap assets' },
  'Utilities & Internet': { line: 'Line 25 · Utilities', hint: 'Telecom' },
  'Transfer / Not Spending': { line: 'Non-Taxable', hint: 'Internal' },
  Refund: { line: 'Income Offset', hint: 'Credits' },
  'Needs Review': { line: 'Action Required', hint: 'Manual' },
}

export function scheduleCMeta(category: string): { line: string; hint: string } {
  const meta = SCHEDULE_C_LINES[category]
  if (meta) return { line: meta.line, hint: meta.hint ?? '' }
  return { line: 'Schedule C', hint: 'Review' }
}
