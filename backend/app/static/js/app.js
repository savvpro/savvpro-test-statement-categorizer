/**
 * LedgerLens — app.js
 * Progressive-enhancement JavaScript for async interactions.
 * No frameworks; vanilla JS only.
 */

'use strict';

/* ── Confidence bar ─────────────────────────────────────── */
function buildConfidenceBars() {
  document.querySelectorAll('[data-confidence]').forEach(el => {
    const score = parseFloat(el.dataset.confidence);
    const pct   = Math.round(score * 100);
    const cls   = score >= 0.80 ? 'high' : score >= 0.50 ? 'medium' : 'low';
    el.innerHTML = `
      <div class="confidence-bar">
        <div class="confidence-track">
          <div class="confidence-fill ${cls}" style="width:${pct}%"></div>
        </div>
        <span class="confidence-text">${pct}%</span>
      </div>`;
  });
}

/* ── Category badge helper ─────────────────────────────── */
const BADGE_MAP = {
  'Software':                    'badge-software',
  'Cloud Hosting':               'badge-cloud-hosting',
  'Hardware and Equipment':      'badge-hardware',
  'Internet and Telecommunications': 'badge-internet',
  'Office Supplies':             'badge-office',
  'Advertising and Marketing':   'badge-advertising',
  'Professional Services':       'badge-professional',
  'Travel':                      'badge-travel',
  'Meals':                       'badge-meals',
  'Bank Fees':                   'badge-bank-fees',
  'Business Income':             'badge-income',
  'Refund':                      'badge-refund',
  'Reversal':                    'badge-reversal',
  'Internal Transfer':           'badge-transfer',
  'Personal Expense':            'badge-personal',
  'Needs Review':                'badge-review',
};

function categoryBadgeClass(name) {
  return BADGE_MAP[name] || 'badge-review';
}

/* ── Inline category correction ────────────────────────── */
function initCategorySelects() {
  document.querySelectorAll('.inline-cat-select').forEach(sel => {
    sel.addEventListener('change', async function () {
      const txId      = this.dataset.txId;
      const categoryId = parseInt(this.value);
      const indicator = document.getElementById(`save-${txId}`);

      try {
        const res = await fetch(`/api/transactions/${txId}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ category_id: categoryId }),
        });

        if (res.ok) {
          const data = await res.json();
          // Update badge in the same row
          const badge = document.getElementById(`cat-badge-${txId}`);
          if (badge) {
            badge.className = `ll-badge ${categoryBadgeClass(data.category_name)}`;
            badge.textContent = data.category_name;
          }
          // Update review status badge
          const statusBadge = document.getElementById(`review-badge-${txId}`);
          if (statusBadge && data.review_status === 'REVIEWED') {
            statusBadge.className = 'll-badge badge-reviewed';
            statusBadge.textContent = 'Reviewed';
          }
          if (indicator) {
            indicator.textContent = '✓ Saved';
            indicator.className = 'save-indicator success show';
            setTimeout(() => indicator.classList.remove('show'), 2500);
          }
        } else {
          const err = await res.json();
          if (indicator) {
            indicator.textContent = '✗ Error';
            indicator.className = 'save-indicator error show';
            setTimeout(() => indicator.classList.remove('show'), 3000);
          }
          console.error('Failed to update transaction', err);
        }
      } catch (e) {
        console.error('Network error', e);
        if (indicator) {
          indicator.textContent = '✗ Network error';
          indicator.className = 'save-indicator error show';
          setTimeout(() => indicator.classList.remove('show'), 3000);
        }
      }
    });
  });
}

/* ── Upload drag-and-drop zone ─────────────────────────── */
function initFileZone() {
  const zone  = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');
  const label = document.getElementById('file-label');

  if (!zone || !input) return;

  zone.addEventListener('click', () => input.click());

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('dragging');
  });

  zone.addEventListener('dragleave', () => zone.classList.remove('dragging'));

  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('dragging');
    if (e.dataTransfer.files.length) {
      input.files = e.dataTransfer.files;
      updateFileLabel(e.dataTransfer.files[0].name);
    }
  });

  input.addEventListener('change', () => {
    if (input.files.length) updateFileLabel(input.files[0].name);
  });

  function updateFileLabel(name) {
    if (label) label.textContent = name;
  }
}

/* ── Flash messages auto-dismiss ───────────────────────── */
function initAlerts() {
  document.querySelectorAll('.ll-alert[data-dismiss]').forEach(el => {
    const delay = parseInt(el.dataset.dismiss || '4000');
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 400);
    }, delay);
  });
}

/* ── Category chart on dashboard ──────────────────────── */
function initCategoryChart() {
  const canvas = document.getElementById('category-chart');
  if (!canvas || typeof Chart === 'undefined') return;

  const labels = JSON.parse(canvas.dataset.labels || '[]');
  const values = JSON.parse(canvas.dataset.values || '[]');

  // Palette of 16 harmonious colours matching semantic CSS badges
  const PALETTE = [
    '#58a6ff', '#3fb950', '#f0883e', '#a371f7',
    '#e3b341', '#79c0ff', '#ffa657', '#d2a8ff',
    '#56d364', '#f85149', '#8b949e', '#d29922',
    '#39d353', '#f778ba', '#db6d28', '#2ea043',
  ];
  const bgColors = values.map((_, i) => PALETTE[i % PALETTE.length]);

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: bgColors,
        borderWidth: 2,
        borderColor: '#161b22',
        hoverBorderColor: '#21262d',
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '72%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#8b949e',
            boxWidth: 12,
            padding: 14,
            font: { family: 'Inter', size: 12 },
          },
        },
        tooltip: {
          callbacks: {
            label: ctx => ` $${parseFloat(ctx.raw).toFixed(2)}`,
          },
        },
      },
    },
  });
}

/* ── Init ───────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  buildConfidenceBars();
  initCategorySelects();
  initFileZone();
  initAlerts();
  initCategoryChart();
});
